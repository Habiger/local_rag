import logging
import json
import sys

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log = {
            "ts": self.formatTime(record),
            "level": record.levelname,
            "msg": record.getMessage(),
            
        }
        if hasattr(record, "extra"): # 
            print(record)
            log.update(record.extra)  # type: ignore
        return json.dumps(log)

logger = logging.getLogger("pipeline")
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JsonFormatter())
logger.addHandler(handler)
logger.setLevel(logging.INFO)