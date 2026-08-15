import logging
import os

logger = logging.getLogger(__name__)

_model = None

def _get_model():
    from doctr.models import ocr_predictor
    global _model
    if _model is None:
        _model = ocr_predictor(det_arch='db_resnet50', reco_arch='crnn_vgg16_bn', pretrained=True)
    return _model

def _render(doctr_res):
    text = ""
    for page in doctr_res.pages:
        for block in page.blocks:
            for line in block.lines:
                words = [w.value for w in line.words]
                text += " ".join(words) + "\n"
    return text.encode('utf-8')

def to_text(path):
    try:
        from doctr.io import DocumentFile
        if str(path).lower().endswith(".pdf"):
            doc = DocumentFile.from_pdf(path)
        else:
            doc = DocumentFile.from_images(path)
            
        res = _get_model()(doc)
        return _render(res)
    except Exception as e:
        logger.error(f"doctr extraction failed: {e}")
        return b""
