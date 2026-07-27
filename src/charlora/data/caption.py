from pathlib import Path
import json
import argparse


def build_caption(meta, leading_tag):
    general_tags = meta["tag_string_general"]. split(" ")
    artist = meta["tag_string_artist"]
    gefilterte_tags = []
    ausschluss_tags = ["artist_name", "signature", "twitter_username", "patreon_username", "watermark", "web_address"]
    for l in general_tags:
        if l not in ausschluss_tags:
            gefilterte_tags.append(l)
    gefilterte_tags.insert(0, leading_tag)
    if artist:
        gefilterte_tags.insert(1, f"artist:{artist}")
    caption = ", ".join(gefilterte_tags)
    return caption

def caption_directory(dir_path, leading_tag):
    for element in dir_path.glob("*.json"):
        with open(element) as datei:
            datei_dict = json.load(datei)
            caption = build_caption(datei_dict, leading_tag)
        pfad = element.with_suffix(".txt")
        with open(pfad, "w") as neue_datei:
            neue_datei.write(caption)


def main() -> None:
    parser = argparse.ArgumentParser(description = "caption skript")     
    parser.add_argument("--dir", required = True, help = "Directory of the images")
    parser.add_argument("--leading_tag", required = True, help = "The character we want to generate images of" )
    args = parser.parse_args()

    caption_directory(Path(args.dir), args.leading_tag)

if __name__ == "__main__":
    main()















