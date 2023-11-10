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
import sys
import urllib

load_dotenv()
# Define API keys and voice ID
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
ELEVENLABS_API_KEY = os.getenv('ELEVEN_API_KEY')
VOICE_ID = 't4WuSgeGcJTpKe7R5Uat' # "ZL0YSbWI2pY7FXL29qpo"
DEEPGRAM_API_KEY = os.getenv('DEEPGRAM_API_KEY')
# Initialize Deepgram client
client = Deepgram(DEEPGRAM_API_KEY)

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 1000

# Set OpenAI API key
openai.api_key = OPENAI_API_KEY

start_time = time.time()
global messages
messages = [{"role": "system", "content": open('prompt.txt', 'r').read()}]



async def run_loop():
    audio_queue = asyncio.Queue()
    start_event = asyncio.Event()  # Create an Event
    semaphore = asyncio.Semaphore(1)  # Create a Semaphore

    async def send_post_requests(endpoints):
        return
        timeout = aiohttp.ClientTimeout(total=1)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for endpoint in endpoints:
                # print(f"making request to endpoint: {endpoint}")
                async with session.get(f'http://192.168.86.154/{endpoint}') as resp:
                    print(resp.status)
                    print(await resp.text())

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
        if not semaphore.locked():
            await semaphore.acquire()
            print("AI started speaking")
        async for chunk in audio_stream:
            if chunk:
                mpv_process.stdin.write(chunk)
                mpv_process.stdin.flush()
        if mpv_process.stdin:
            mpv_process.stdin.close()
        mpv_process.wait()
        if semaphore.locked():
            print("AI finished speaking")
            semaphore.release()

    async def text_to_speech_input_streaming(voice_id, text_iterator):
        """Send text to ElevenLabs API and stream the returned audio."""
        uri = f"wss://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream-input?model_id=eleven_turbo_v2"

        async with websockets.connect(uri) as websocket:
            await websocket.send(json.dumps({
                "text": " ",
                "voice_settings": {"stability": 0.2, "similarity_boost": True},
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
        global messages
        new_messages = messages + [{'role': 'user', 'content': query}]
        response = await openai.ChatCompletion.acreate(
            model='gpt-3.5-turbo', messages=new_messages,
            temperature=1, stream=True
        )
        messages = new_messages

        async def text_iterator():
            generated_response = ""
            async for chunk in response:
                delta = chunk['choices'][0]["delta"]
                if 'content' in delta:
                    generated_response += delta["content"]
                    yield delta["content"]
                else:
                    break
            messages.append({'role': 'assistant', 'content': generated_response})
            print("generating text took", time.time() - start_time, "seconds")

        await text_to_speech_input_streaming(VOICE_ID, text_iterator())

    # Used for microphone streaming only.
    def mic_callback(input_data, frame_count, time_info, status_flag):
        if not semaphore.locked():
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

    # Open a websocket connection
    query_params = {
        'model': 'general',
        'interim_results': 'true',
        'endpointing': 'true',
        'encoding': 'linear16',
        'sample_rate': RATE,
        'punctuation': 'true',
        'profanity_filter': 'false',
        'smart_formatting': 'true',
        'redaction': 'false',
        'channels': '1',
        'keywords': "rm&rf"
    }
    query_string = '&'.join([f'{k}={urllib.parse.quote_plus(str(v))}' for k, v in query_params.items()])
    async with websockets.connect(f'wss://api.deepgram.com/v1/listen?{query_string}', extra_headers = { 'Authorization': f'token {DEEPGRAM_API_KEY}' }) as ws:
        # If the request is successful, print the request ID from the HTTP header
        print('🟢 Successfully opened connection')
        print(f'Request ID: {ws.response_headers["dg-request-id"]}')

        async def send_speech_to_text_stream():
            nonlocal ws
            """Stream audio from the microphone to Deepgram using websockets."""
            await start_event.wait()
            print("microphone started")
            try:    
                while True:
                    print("Connecting to send audio to deepgram for transcriptions.")
                    try:
                        while True:
                            if semaphore.locked():
                                # print("AI is speaking, skipping mic data", end='\r', flush=True)
                                await ws.send(json.dumps({ "type": "KeepAlive" }))
                            else:
                                mic_data = await audio_queue.get()
                                await ws.send(mic_data)
                    except websockets.exceptions.ConnectionClosedError:
                        print("Connection closed unexpectedly. Reconnecting...")
                        ws = await websockets.connect(f'wss://api.deepgram.com/v1/listen?{query_string}', extra_headers = { 'Authorization': f'token {DEEPGRAM_API_KEY}' })
                        print('🟢 Successfully reopened connection')
                        print(f'Request ID: {ws.response_headers["dg-request-id"]}')
                    except websockets.exceptions.InvalidStatusCode as e:
                        # If the request fails, print both the error message and the request ID from the HTTP headers
                        print(f'🔴 ERROR: Could not connect to Deepgram! {e.headers.get("dg-error")}')
                        print(f'🔴 Please contact Deepgram Support with request ID {e.headers.get("dg-request-id")}')
            except KeyboardInterrupt as _:
                await ws.send(json.dumps({
                    'type': 'CloseStream'
                }))
                print(f'🔴 ERROR: Closed stream via keyboard interrupt')

        async def receive_speech_to_text_stream():
            nonlocal ws
            """Receive text from Deepgram and pass it to the chat completion function."""
            while True:
                print("Connecting to receive transcriptions")
                try:
                    while True:
                        response = await ws.recv()
                        data = json.loads(response)
                        if data.get('type') == 'Results':
                            channel = data.get('channel')
                            alternatives = channel.get('alternatives')
                            if alternatives and len(alternatives) > 0:
                                first_result = alternatives[0]
                                transcript = first_result.get('transcript')
                                if data.get('is_final'):
                                    print('\r' + ' ' * len(transcript), end='')  # Clear the previous line
                                    print('\r Replying to: ' + transcript, end='')  # Write over the cleared line
                                    if(len(transcript) > 0):
                                        asyncio.create_task(send_post_requests(['eyes/dim', '/movement/stop'])) # stop the animation when the user is done speaking
                                        await chat_completion(transcript)
                                else:
                                    if(len(transcript.split(' ')) == 1):
                                        asyncio.create_task(send_post_requests(['eyes/bright', '/movement/start'])) # start the animation when the user starts speaking
                                    print('\r' + ' ' * len(transcript), end='')
                                    print('\r' + transcript, end='')
                            else:
                                transcript = ""
                            
                except websockets.exceptions.ConnectionClosed:
                    print("Transcription connection closed")

        return await asyncio.gather(
            asyncio.ensure_future(microphone()),
            asyncio.ensure_future(send_speech_to_text_stream()),
            asyncio.ensure_future(receive_speech_to_text_stream()),
        )

# Main execution
if __name__ == "__main__":
    user_query = "Hello, tell me a story that's only 1 sentence long."

    asyncio.run(run_loop())
    # asyncio.run(chat_completion(user_query))