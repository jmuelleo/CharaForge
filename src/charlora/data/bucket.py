import math 
from PIL import Image
from pathlib import Path
import json

def compute_target_resolution(width, height, target_area, multiple):
    r = width/height
    neue_höhe = math.sqrt(target_area/r) #target area ist das pixel budget pro bild <- reskalieren entsprechend
    neue_höhe = round(neue_höhe/multiple)*multiple
    neue_breite = math.sqrt(target_area*r)
    neue_breite = round(neue_breite/multiple)*multiple
    return neue_breite, neue_höhe


def bucket_directory(dir_path, target_area, multiple):
    path = Path(dir_path)
    for element in path.glob("*.json"):
        for ext in ["jpg", "jpeg", "png", "webp"]:
            bild_pfad = element.with_suffix("." + ext)
            if bild_pfad.exists():
                break
        with Image.open(bild_pfad) as im:
            breite, höhe = im.size
        neue_breite, neue_höhe =  compute_target_resolution(breite, höhe, target_area, multiple)
        with open(element) as datei:
            datei_dict = json.load(datei)
        with open(element, "w") as datei:
            datei_dict["bucket_width"] = neue_breite
            datei_dict["bucket_height"] = neue_höhe
            json.dump(datei_dict, datei, indent = 2)







    
