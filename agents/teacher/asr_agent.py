import os
import signal
import sys
import dashscope
import pyaudio
from dashscope.audio.asr import *

mic = None
stream = None
last_sentence = ""  # 用于存储最后识别到的句子

# Set recording parameters
sample_rate = 16000  # sampling rate (Hz)
channels = 1  # mono channel
dtype = 'int16'  # data type
format_pcm = 'pcm'  # the format of the audio data
block_size = 3200  # number of frames per buffer


def init_dashscope_api_key():
    """
        Set your DashScope API-key.
    """
    if 'DASHSCOPE_API_KEY' in os.environ:
        dashscope.api_key = os.environ['DASHSCOPE_API_KEY']  # load API-key from environment variable DASHSCOPE_API_KEY
    else:
        dashscope.api_key = '<your-dashscope-api-key>'  # set API-key manually


# Real-time speech recognition callback
class Callback(RecognitionCallback):
    def on_open(self) -> None:
        global mic
        global stream
        print('RecognitionCallback open.')
        try:
            mic = pyaudio.PyAudio()
            stream = mic.open(format=pyaudio.paInt16,
                              channels=1,
                              rate=16000,
                              input=True)
            print("Audio stream opened successfully.")
        except Exception as e:
            print(f"Error opening audio stream: {e}")
            sys.exit(1)

    def on_close(self) -> None:
        global mic
        global stream
        print('RecognitionCallback close.')
        if stream:
            stream.stop_stream()
            stream.close()
        if mic:
            mic.terminate()
        stream = None
        mic = None

    def on_complete(self) -> None:
        print('RecognitionCallback completed.')  # translation completed

    def on_error(self, message) -> None:
        print('RecognitionCallback task_id: ', message.request_id)
        print('RecognitionCallback error: ', message.message)
        # Stop and close the audio stream if it is running
        if 'stream' in globals() and stream.active:
            stream.stop()
            stream.close()
        # Forcefully exit the program
        sys.exit(1)

    def on_event(self, result: RecognitionResult) -> None:
        global last_sentence  # Declare last_sentence as global so we can update it
        sentence = result.get_sentence()
        if 'text' in sentence:
            last_sentence = sentence['text']  # Update the last recognized sentence
            print(f"Recognized text: {last_sentence}")  # Print recognized text for debugging


# Keyboard interrupt handler
def signal_handler(sig, frame):
    print('Ctrl+C pressed, stop translation ...')
    recognition.stop()
    print('Translation stopped.')
    print(
        '[Metric] requestId: {}, first package delay ms: {}, last package delay ms: {}'
        .format(
            recognition.get_last_request_id(),
            recognition.get_first_package_delay(),
            recognition.get_last_package_delay(),
        ))
    sys.exit(0)


# Main function
if __name__ == '__main__':
    init_dashscope_api_key()
    print('Initializing ...')

    # Create the translation callback
    callback = Callback()

    # Call recognition service by async mode
    recognition = Recognition(
        model='paraformer-realtime-v2',
        format=format_pcm,
        sample_rate=sample_rate,
        semantic_punctuation_enabled=False,
        callback=callback)

    # Start translation
    recognition.start()

    # Set up signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    print("Press 'Ctrl+C' to stop recording and translation...")

    # Process a single frame of audio, recognize the speech, and stop.
    if stream:
        print("Reading audio stream...")
        data = stream.read(3200, exception_on_overflow=False)
        print(f"Audio data read: {len(data)} bytes")
        recognition.send_audio_frame(data)
    else:
        print("Audio stream is not available. Exiting.")

    recognition.stop()

    # Output the last recognized sentence after processing
    print(f"Last recognized sentence: {last_sentence}")
