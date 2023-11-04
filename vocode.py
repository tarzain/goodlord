from vocode.streaming.models.transcriber import WhisperCPPTranscriberConfig
from vocode.streaming.transcriber.whisper_cpp_transcriber import WhisperCPPTranscriber

StreamingConversation(
    ...
    transcriber=WhisperCPPTranscriber(
        WhisperCPPTranscriberConfig.from_input_device(
            microphone_input,
            libname="/whisper.cpp/libwhisper.so",
            fname_model="/whisper.cpp/models/ggml-tiny.bin",
        )
    )
    ...
)

from vocode.streaming.models.agent import GPT4AllAgentConfig
from vocode.streaming.agent.gpt4all_agent import GPT4AllAgent

StreamingConversation(
    ...
    agent=GPT4AllAgent(
        GPT4AllAgentConfig(
            model_path="path/to/ggml-gpt4all-j-...-.bin",
            initial_message=BaseMessage(text="Hello!"),
            prompt_preamble="The AI is having a pleasant conversation about life"
        )
    )
    ...
)

from vocode.streaming.models.agent import LlamacppAgentConfig
from vocode.streaming.agent.llamacpp_agent import LlamacppAgent

StreamingConversation(
    ...
    agent=LlamacppAgent(
        LlamacppAgentConfig(
            prompt_preamble="The AI is having a pleasant conversation about life",
            llamacpp_kwargs={"model_path": "path/to/nous-hermes-13b.ggmlv3.q4_0.bin", "verbose": True},
            prompt_template="alpaca",
            initial_message=BaseMessage(text="Hello!"),
        )
    )
    ...
)

from vocode.streaming.models.synthesizer import CoquiTTSSynthesizerConfig,
from vocode.streaming.synthesizer.coqui_tts_synthesizer import CoquiTTSSynthesizer

StreamingConversation(
    ...
    synthesizer=CoquiTTSSynthesizer(
        CoquiTTSSynthesizerConfig.from_output_device(
            speaker_output,
            tts_kwargs = {
                "model_name": "tts_models/en/ljspeech/tacotron2-DDC_ph"
            }
        )
    )
    ...
)

StreamingConversation(
    output_device=speaker_output,
    transcriber=WhisperCPPTranscriber(
        WhisperCPPTranscriberConfig.from_input_device(
            microphone_input,
            libname="path/to/whisper.cpp/libwhisper.so",
            fname_model="path/to/whisper.cpp/models/ggml-tiny.bin",
        )
    ),
    agent=GPT4AllAgent(
        GPT4AllAgentConfig(
            model_path="path/to/ggml-...-.bin",
            initial_message=BaseMessage(text="Hello!"),
            prompt_preamble="The AI is having a pleasant conversation about life"
        )
    ),
    synthesizer=CoquiTTSSynthesizer(
        CoquiTTSSynthesizerConfig.from_output_device(
            speaker_output,
            tts_kwargs = {
                "model_name": "tts_models/en/ljspeech/tacotron2-DDC_ph"
            }
        )
    ),
    logger=logger,
)