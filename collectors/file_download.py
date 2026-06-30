"""安全下载公开 Excel/CSV/PDF 附件。"""

import hashlib
import re
from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen

from db import BASE_DIR


ALLOWED_EXTENSIONS = {".xlsx", ".xls", ".csv", ".pdf"}
MAX_FILE_SIZE = 30 * 1024 * 1024
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def _safe_filename_from_url(url: str) -> str:
    parsed = urlparse(url)
    name = unquote(Path(parsed.path).name)
    suffix = Path(name).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        suffix = ".bin"
    if not name or name == suffix:
        name = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16] + suffix
    name = re.sub(r'[\\/:*?"<>|\s]+', "_", name).strip("._")
    if Path(name).suffix.lower() not in ALLOWED_EXTENSIONS:
        name += suffix
    return name


def download_file(url: str, target_dir: str = "data_downloads") -> dict:
    target_path = BASE_DIR / target_dir
    target_path.mkdir(exist_ok=True)

    filename = _safe_filename_from_url(url)
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        return {
            "status": "failed",
            "local_file_path": None,
            "file_size": 0,
            "message": f"不允许下载的文件类型：{suffix}",
        }

    local_file = target_path / filename
    try:
        request = Request(url, headers=REQUEST_HEADERS)
        size = 0
        with urlopen(request, timeout=30) as response:
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > MAX_FILE_SIZE:
                return {
                    "status": "failed",
                    "local_file_path": None,
                    "file_size": 0,
                    "message": "文件超过 30MB，已跳过",
                }

            with local_file.open("wb") as file:
                while True:
                    chunk = response.read(1024 * 128)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > MAX_FILE_SIZE:
                        file.close()
                        local_file.unlink(missing_ok=True)
                        return {
                            "status": "failed",
                            "local_file_path": None,
                            "file_size": size,
                            "message": "文件超过 30MB，已停止下载",
                        }
                    file.write(chunk)

        return {
            "status": "success",
            "local_file_path": str(local_file),
            "file_size": size,
            "message": "下载成功",
        }
    except Exception as exc:
        return {
            "status": "failed",
            "local_file_path": None,
            "file_size": 0,
            "message": str(exc),
        }
