import os
import subprocess
import tempfile
from fastapi import HTTPException
from app.config import WHISPER_EXECUTABLE, MODEL_PATH, TEMP_DIR

async def transcribe_audio(file):
    """Transcribe audio file using whisper.cpp."""
    file_size = 0
    chunk_size = 1024 * 1024  # 1MB chunks
    temp_file_path = None
    wav_file_path = None
    
    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename),[object Object],) as temp_file:
            temp_file_path = temp_file.name

            # Read and save file
            while chunk := await file.read(chunk_size):
                file_size += len(chunk)
                if file_size > 25 * 1024 * 1024:  # 25MB limit
                    raise HTTPException(status_code=413, detail="File too large. Max size is 25MB")
                temp_file.write(chunk)

        # Convert to WAV if needed
        wav_file_path = temp_file_path if temp_file_path.endswith('.wav') else temp_file_path.rsplit('.', 1),[object Object], + '.wav'
        if not temp_file_path.endswith('.wav'):
            subprocess.run([
                'ffmpeg', '-i', temp_file_path,
                '-ar', '16000',  # 16kHz sample rate
                '-ac', '1',      # mono
                '-c:a', 'pcm_s16le',
                wav_file_path
            ], check=True, capture_output=True)

        # Run whisper executable
        if not os.path.exists(WHISPER_EXECUTABLE):
            raise HTTPException(status_code=500, detail="Whisper executable not found.")

        result = subprocess.run([
            WHISPER_EXECUTABLE,
            '-m', MODEL_PATH,
            '-f', wav_file_path,
            '-nt'  # No timestamps
        ], capture_output=True, text=True, check=True)

        # Extract transcription from output
        output = result.stdout
        lines = output.split('\n')
        transcription_lines = [line.strip() for line in lines if line.strip() and not line.startswith('[')]
        return ' '.join(transcription_lines)

    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Whisper transcription failed: {e.stderr}")
    finally:
        # Cleanup temporary files
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        if wav_file_path and wav_file_path != temp_file_path and os.path.exists(wav_file_path):
            os.unlink(wav_file_path)
