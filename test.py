import asyncio
import websockets
import json
import openai
import base64
import shutil
import os
import subprocess
import time
from dotenv import load_dotenv
from elevenlabs import voices, generate, stream, set_api_key
from deepgram import Deepgram
import aiohttp
import pyaudio

load_dotenv()
# Define API keys and voice ID
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
ELEVENLABS_API_KEY = os.getenv('ELEVEN_API_KEY')
VOICE_ID = '21m00Tcm4TlvDq8ikWAM'
DEEPGRAM_API_KEY = os.getenv('DEEPGRAM_API_KEY')
# Initialize Deepgram client
client = Deepgram(DEEPGRAM_API_KEY)

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 2048

# Set OpenAI API key
openai.api_key = OPENAI_API_KEY

start_time = time.time()

def is_installed(lib_name):
    return shutil.which(lib_name) is not None


async def text_chunker(chunks):
    """Split text into chunks, ensuring to not break sentences."""
    splitters = (".", ",", "?", "!", ";", ":", "—", "-", "(", ")", "[", "]", "}", " ")
    buffer = ""

    async for text in chunks:
        if buffer.endswith(splitters):
            yield buffer + " "
            buffer = text
        elif text.startswith(splitters):
            yield buffer + text[0] + " "
            buffer = text[1:]
        else:
            buffer += text

    if buffer:
        yield buffer + " "


async def stream(audio_stream):
    """Stream audio data using mpv player."""
    if not is_installed("mpv"):
        raise ValueError(
            "mpv not found, necessary to stream audio. "
            "Install instructions: https://mpv.io/installation/"
        )

    mpv_process = subprocess.Popen(
        ["mpv", "--no-cache", "--no-terminal", "--", "fd://0"],
        stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

    print("Started streaming audio")
    async for chunk in audio_stream:
        if chunk:
            mpv_process.stdin.write(chunk)
            mpv_process.stdin.flush()

    if mpv_process.stdin:
        mpv_process.stdin.close()
    mpv_process.wait()


async def text_to_speech_input_streaming(voice_id, text_iterator):
    """Send text to ElevenLabs API and stream the returned audio."""
    uri = f"wss://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream-input?model_id=eleven_monolingual_v1"

    async with websockets.connect(uri) as websocket:
        await websocket.send(json.dumps({
            "text": " ",
            "voice_settings": {"stability": 0.5, "similarity_boost": True},
            "xi_api_key": ELEVENLABS_API_KEY,
            "optimize_streaming_latency": 3,
        }))

        async def listen():
            """Listen to the websocket for audio data and stream it."""
            while True:
                try:
                    message = await websocket.recv()
                    data = json.loads(message)
                    if data.get("audio"):
                        yield base64.b64decode(data["audio"])
                    elif data.get('isFinal'):
                        break
                except websockets.exceptions.ConnectionClosed:
                    print("Connection closed")
                    break

        listen_task = asyncio.create_task(stream(listen()))

        async for text in text_chunker(text_iterator):
            await websocket.send(json.dumps({"text": text, "try_trigger_generation": True}))

        await websocket.send(json.dumps({"text": ""}))

        await listen_task


async def chat_completion(query):
    """Retrieve text from OpenAI and pass it to the text-to-speech function."""
    response = await openai.ChatCompletion.acreate(
        model='gpt-4', messages=[{'role': 'user', 'content': query}],
        temperature=1, stream=True
    )

    async def text_iterator():
        async for chunk in response:
            delta = chunk['choices'][0]["delta"]
            if 'content' in delta:
                yield delta["content"]
            else:
                break
        print("generating text took", time.time() - start_time, "seconds")

    await text_to_speech_input_streaming(VOICE_ID, text_iterator())


async def run_loop():
    audio_queue = asyncio.Queue()
    start_event = asyncio.Event()  # Create an Event

    # Used for microphone streaming only.
    def mic_callback(input_data, frame_count, time_info, status_flag):
        audio_queue.put_nowait(input_data)
        return (input_data, pyaudio.paContinue)
    
    # Set up microphone if streaming from mic
    async def microphone():
        audio = pyaudio.PyAudio()
        stream = audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
            stream_callback=mic_callback,
        )

        stream.start_stream()
        start_event.set()  # Set the event to trigger the other coroutines to start

        global SAMPLE_SIZE
        SAMPLE_SIZE = audio.get_sample_size(FORMAT)

        while stream.is_active():
            await asyncio.sleep(0.1)

        stream.stop_stream()
        stream.close()

    async def speech_to_text_stream():
        """Stream audio from the microphone to Deepgram."""
        await start_event.wait()
        print("microphone started")
        # Open a streaming session
        try:
            deepgramLive = await client.transcription.live(
                { "model": "nova", "language": "en-US", 'punctuate': True, 'interim_results': True }
            )
        except Exception as e:
            print(f'Could not open socket: {e}')
            return
        

        # Listen for the connection to close
        deepgramLive.registerHandler(deepgramLive.event.CLOSE, lambda c: print(f"Connection closed with code {c}"))
        
        # Listen for any transcripts received from Deepgram and write them to the console
        deepgramLive.registerHandler(deepgramLive.event.TRANSCRIPT_RECEIVED, print)
        
        # Start streaming
        while True:
            mic_data = await audio_queue.get()
            print(f"sending data to deepgram: {len(mic_data)}")
            deepgramLive.send(mic_data)

    return await asyncio.gather(
        asyncio.ensure_future(microphone()),
        asyncio.ensure_future(speech_to_text_stream()),
    )

# Main execution
if __name__ == "__main__":
    user_query = "Hello, tell me a story that's only 1 sentence long."

    asyncio.run(run_loop())
    # asyncio.run(chat_completion(user_query))


