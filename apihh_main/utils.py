from moviepy.video.io.VideoFileClip import VideoFileClip

MAX_VIDEO_SIZE_MB = 100
MIN_DURATION = 5
MAX_DURATION = 90

def validate_video(file_path, file_size):
    errors = []

    if file_size > MAX_VIDEO_SIZE_MB * 1024 * 1024:
        errors.append('Видео слишком большое')

    try:
        clip = VideoFileClip(file_path)

        width, height = clip.size
        duration = clip.duration

        clip.close()

        # разрешаем 9:16, 1:1, 4:5
        if width > height:
            errors.append('Горизонтальные видео запрещены')

        if duration < MIN_DURATION or duration > MAX_DURATION:
            errors.append('Недопустимая длительность видео')

    except Exception as e:
        errors.append(f'Ошибка обработки видео: {str(e)}')

    return errors
