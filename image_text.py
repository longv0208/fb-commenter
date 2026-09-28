async def read_png(png_bytes):
    """Read Latin text from a screenshot. Returns an empty string if OCR is unavailable."""
    try:
        from io import BytesIO

        import winocr
        from PIL import Image

        image = Image.open(BytesIO(png_bytes))
        result = await winocr.to_coroutine(winocr.recognize_pil(image, "en"))
        return " ".join(line.text for line in result.lines if getattr(line, "text", ""))
    except Exception:
        return ""
