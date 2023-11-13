# Goodlord
_a streaming voice AI using OpenAI, Deepgram, and ElevenLabs_

This project requires Python 3.9 and a few dependencies. Follow the steps below to set up your environment.

## Step 1: Create a Conda Environment

First, create a new Conda environment with Python 3.9. You can do this using the following command:

```bash
conda create --name goodlord python=3.9
```

Activate the environment using:

```bash
conda activate goodlord
```

## Step 2: Install Dependencies

Next, install the required dependencies. You can do this using the following command:

```bash
pip install -r requirements.txt
```

You may also need to install `mpv` a cross platform media player that we use to stream audio from the text to speech API. On mac os, you can do this with homebrew easily:
```bash
brew install mpv
```


## Step 3: Setup Environment Variables

Create a `.env.secret` file in the project root directory.
```bash
cp .env.example .env.secret
```

Add the following environment variables:

```bash
OPENAI_API_KEY=your_openai_api_key
ELEVENLABS_API_KEY=your_elevenlabs_api_key
DEEPGRAM_API_KEY=your_deepgram_api_key
ELEVEN_LABS_VOICE_ID=your_eleven_labs_voice_id
```

Replace `your_openai_api_key`, `your_elevenlabs_api_key`, `your_deepgram_api_key`, and `your_eleven_labs_voice_id` with your actual API keys.

## Step 4: Run the Code

Finally, you can run the code using the following command:

```bash
python main.py
```
## Step 5: Monitor the Output

After running the code, you should see the output in your terminal. If there are any errors, they will also be displayed in the terminal.

## Step 6: Stop the Program

To stop the program, use the following command:

```bash
CTRL+C
```

This will stop the execution of the program.

## Troubleshooting

If you encounter any issues while running the program, please check the following:

1. Ensure that all the dependencies are installed correctly.
2. Verify that the API keys are correct.
3. Make sure that the Python version is 3.9.

If the problem persists, please create an issue on Github!


