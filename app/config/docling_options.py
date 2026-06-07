from docling_serve.datamodel.convert import ConvertDocumentsRequestOptions
from docling.datamodel.base_models import InputFormat, OutputFormat
from docling.datamodel.pipeline_options import PdfBackend, TableFormerMode
from docling_core.types.doc.base import ImageRefMode

convert_options_json = ConvertDocumentsRequestOptions(
    from_formats=[InputFormat.PDF],
    to_formats=[OutputFormat.JSON, OutputFormat.MARKDOWN],
    image_export_mode=ImageRefMode.REFERENCED,
    #ocr_custom_config={ # does already specify "easyocr" as ocr engine
    #        "kind": "easyocr",
    #        "lang": ["en", "de"],
    #        "bitmap_area_threshold": 0.05,
    #        "confidence_threshold": 0.5,
    #        "download_enabled": False,
    #        "kind": "easyocr" # is included in EasyOcrOptions as a ClassVar which is not considered a field, thus not dumped via model_dump
    #},
    ocr_custom_config={ # does already specify "easyocr" as ocr engine
            "kind": "rapidocr",
            "lang": ["english", "chinese"],
            "bitmap_area_threshold": 0.05,
    },
    do_ocr=True,
    #force_ocr=False, # already included in ocr_custom_config
    pdf_backend=PdfBackend.DOCLING_PARSE,
    table_mode=TableFormerMode.ACCURATE,
    do_table_structure=True,
    do_formula_enrichment=True,
    do_picture_description=True,
    picture_description_area_threshold=0.05,
    vlm_pipeline_preset="granite_docling"
    )

convert_options = ConvertDocumentsRequestOptions(
    from_formats=[InputFormat.PDF],
    to_formats=[OutputFormat.JSON, OutputFormat.MARKDOWN],
    image_export_mode=ImageRefMode.REFERENCED,
    do_ocr=False,
    force_ocr=False,
    ocr_preset="easyocr",
    ocr_lang=["en", "de"],
    pdf_backend=PdfBackend.DOCLING_PARSE,
    table_mode=TableFormerMode.ACCURATE,
    do_table_structure=True,
    do_formula_enrichment=True,
    do_picture_description=True,
    picture_description_area_threshold=0.05,
    vlm_pipeline_preset="granite_docling"
    )

