import openai
from elevenlabs import generate, stream, set_api_key
import sys
import time
from dotenv import load_dotenv
import os
from typing import Iterator

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")
set_api_key(os.getenv("ELEVEN_API_KEY"))
global AI_SPEAKING
AI_Speaking = False

def text_stream():
  # record the time before the request is sent
  start_time = time.time()

  response = openai.ChatCompletion.create(
    model='gpt-3.5-turbo',
    messages=[
        {'role': 'user', 'content': "Hello, tell me a story that's only 3 sentences long."}
    ],
    temperature=1,
    stream=True  # this time, we set stream=True
  )

  for chunk in response:
    # record the time after each chunk is received
    end_time = time.time()
    # calculate the time difference
    time_diff = end_time - start_time
    # check if chunk has choices
    if(len(chunk['choices']) and (hasattr(chunk['choices'][0], 'delta') and hasattr(chunk['choices'][0]['delta'], 'content'))):
      yield chunk['choices'][0]['delta']['content']
  print("Time taken to generate text: " + str(time_diff) + " seconds")

async def text_stream_async():
  """Retrieve text from OpenAI and pass it to the text-to-speech function."""
  response = await openai.ChatCompletion.acreate(
    model='gpt-4', messages=[{'role': 'user', 'content': "Hello, tell me a story that's only 3 sentences long."}],
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

def print_stream():
  for chunk in text_stream():
    print(chunk, sep='', end='', flush=True)

def speak_stream():
  AI_SPEAKING = True
  text_stream_generator = text_stream_async()
  next(text_stream_generator)
  print(isinstance(text_stream_generator, Iterator))
  # record the time before the request is sent
  start_time = time.time()
  audio_stream = generate(
      text=text_stream_generator,
      voice="Nicole",
      model="eleven_multilingual_v2",
      stream=True
  )

  for chunk in audio_stream:
    print('.', sep='', end='', flush=True)

  # stream(audio_stream)
  # print the time taken
  end_time = time.time()
  time_diff = end_time - start_time
  print("Time taken to speak audio: " + str(time_diff) + " seconds")

if __name__ == "__main__":
  # print_stream()
  speak_stream()