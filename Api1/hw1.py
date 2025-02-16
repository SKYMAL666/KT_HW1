from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.responses import FileResponse
from PIL import Image
from moviepy.video.io.VideoFileClip import VideoFileClip
import os
import uuid
from pathlib import Path
from typing import Optional

app = FastAPI()

# Директории для хранения файлов и превью
UPLOAD_FOLDER = Path("files")
PREVIEW_FOLDER = Path("previews")

# Создаем папки, если они не существуют
UPLOAD_FOLDER.mkdir(exist_ok=True)
PREVIEW_FOLDER.mkdir(exist_ok=True)

# Хранилище для информации о файлах
file_storage = {}

# Генерация уникального ID
def generate_file_id():
    return str(uuid.uuid4())

# Генерация превью для изображений
def generate_image_preview(file_path: Path, preview_path: Path, width: int, height: int):
    img = Image.open(file_path)
    img.thumbnail((width, height))
    img.save(preview_path, "JPEG")

# Генерация превью для видео
def generate_video_preview(file_path: Path, preview_path: Path, width: int, height: int):
    clip = VideoFileClip(str(file_path))
    frame = clip.get_frame(0)
    clip.close()

    from PIL import Image as PILImage
    import numpy as np

    img = PILImage.fromarray(frame)
    img.thumbnail((width, height))
    img.save(preview_path, "JPEG")

@app.put("/upload/")
async def upload_file(file: UploadFile = File(...)):
    file_id = generate_file_id()
    file_extension = os.path.splitext(file.filename)[1]
    file_path = UPLOAD_FOLDER / f"{file_id}{file_extension}"

    # Сохраняем файл
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    # Сохраняем информацию о файле
    file_storage[file_id] = {"filename": file.filename, "path": str(file_path)}
    return {"file_id": file_id, "filename": file.filename}

@app.get("/download/{file_id}")
async def download_file(file_id: str, width: Optional[int] = Query(None), height: Optional[int] = Query(None)):
    # Проверяем, существует ли файл
    file_info = file_storage.get(file_id)
    if not file_info:
        raise HTTPException(status_code=404, detail="File not found")

    file_path = Path(file_info["path"])
    file_extension = os.path.splitext(file_path.name)[1].lower()

    # Если запрошено превью
    if width is not None and height is not None:
        preview_path = PREVIEW_FOLDER / f"{file_id}_{width}x{height}.jpg"
        if not preview_path.exists():
            try:
                if file_extension in [".jpg", ".jpeg", ".png", ".gif"]:
                    generate_image_preview(file_path, preview_path, width, height)
                elif file_extension in [".mp4", ".avi", ".mov"]:
                    generate_video_preview(file_path, preview_path, width, height)
                else:
                    raise HTTPException(status_code=400, detail="File format not supported for preview")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error generating preview: {str(e)}")

        return FileResponse(preview_path, media_type="image/jpeg")

    return FileResponse(file_path, filename=file_info["filename"])

@app.get("/files/")
def list_files():
    return {"files": [{"id": file_id, "name": info["filename"]} for file_id, info in file_storage.items()]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)