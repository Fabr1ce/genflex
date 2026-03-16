# Shared media generation tools used by root_agent and sub-agents
# Copyright 2026 Google LLC

import os


def _save_media(data: bytes, filename: str, content_type: str) -> str:
    """Save media to GCS if configured, otherwise to local static/media/."""
    bucket_name = os.environ.get("LOGS_BUCKET_NAME")
    if bucket_name:
        import google.cloud.storage as gcs
        client = gcs.Client()
        blob = client.bucket(bucket_name).blob(f"media/{filename}")
        blob.upload_from_string(data, content_type=content_type)
        return f"gs://{bucket_name}/media/{filename}"
    else:
        media_dir = os.path.join(os.path.dirname(__file__), "..", "static", "media")
        os.makedirs(media_dir, exist_ok=True)
        with open(os.path.join(media_dir, filename), "wb") as f:
            f.write(data)
        return f"/static/media/{filename}"


def sketch_scene(prompt: str) -> str:
    """Generate an image using Imagen and store it.

    Args:
        prompt: Detailed description of the scene to generate

    Returns:
        URI of the generated image, or error message
    """
    import uuid
    from google import genai
    from google.genai import types as gtypes

    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "global")
    client = genai.Client(vertexai=True, project=project, location=location)

    try:
        response = client.models.generate_images(
            model="imagen-3.0-generate-002",
            prompt=prompt,
            config=gtypes.GenerateImagesConfig(number_of_images=1),
        )
        image_bytes = response.generated_images[0].image.image_bytes
        uri = _save_media(image_bytes, f"image-{uuid.uuid4().hex}.png", "image/png")
        return f"[IMAGE: {uri}]"
    except Exception as e:
        return f"[IMAGE_ERROR: {e}]"


def generate_audio_narration(text: str, voice_name: str = "en-US-Journey-F") -> str:
    """Generate TTS audio narration using Google Cloud TTS and store it.

    Args:
        text: The text to convert to speech
        voice_name: Cloud TTS voice (e.g. en-US-Journey-F, en-US-Journey-D)

    Returns:
        URI of the generated audio, or error message
    """
    import uuid
    from google.cloud import texttospeech

    try:
        client = texttospeech.TextToSpeechClient()
        response = client.synthesize_speech(
            input=texttospeech.SynthesisInput(text=text),
            voice=texttospeech.VoiceSelectionParams(
                language_code="en-US",
                name=voice_name,
            ),
            audio_config=texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3
            ),
        )
        uri = _save_media(response.audio_content, f"audio-{uuid.uuid4().hex}.mp3", "audio/mpeg")
        return f"[AUDIO: {uri}]"
    except Exception as e:
        return f"[AUDIO_ERROR: {e}]"


def create_video_segment(image_prompt: str, narration: str, duration: int = 5) -> str:
    """Generate a video using Veo and store it in GCS.

    Args:
        image_prompt: Description of the visual content
        narration: Audio narration text
        duration: Duration in seconds (5 or 8)

    Returns:
        GCS URI of the generated video, or error message
    """
    import time
    import uuid
    from google import genai
    from google.genai import types as gtypes

    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "global")
    bucket_name = os.environ.get("LOGS_BUCKET_NAME")
    if not bucket_name:
        return "[VIDEO_SKIPPED: set LOGS_BUCKET_NAME to enable video generation (Veo requires GCS output)]"

    client = genai.Client(vertexai=True, project=project, location=location)
    output_gcs = f"gs://{bucket_name}/media/video-{uuid.uuid4().hex}/"

    try:
        op = client.models.generate_videos(
            model="veo-2.0-generate-001",
            prompt=f"{image_prompt}. {narration}",
            config=gtypes.GenerateVideosConfig(
                duration_seconds=min(max(duration, 5), 8),
                output_gcs_uri=output_gcs,
                generate_audio=False,
            ),
        )
        while not op.done:
            time.sleep(15)
            op = client.operations.get(op)
        videos = op.result.generated_videos
        if videos:
            return f"[VIDEO: {videos[0].video.uri}]"
        return "[VIDEO_ERROR: no video returned]"
    except Exception as e:
        return f"[VIDEO_ERROR: {e}]"
