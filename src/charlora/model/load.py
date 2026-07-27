
import torch
from diffusers import ChromaPipeline
from diffusers.quantizers import PipelineQuantizationConfig


def load_pipeline(model_id = "lodestones/Chroma1-HD"):
    quant_config = PipelineQuantizationConfig(quant_backend = "bitsandbytes_4bit",
                                              quant_kwargs = {"load_in_4bit": True,
                                                              "bnb_4bit_quant_type": "nf4",
                                                              "bnb_4bit_compute_dtype": torch.bfloat16},
                                              components_to_quantize = ["transformer", "text_encoder"])
    pipe = ChromaPipeline.from_pretrained(model_id,
                                          quantization_config = quant_config,
                                          torch_dtype = torch.bfloat16)
    pipe = pipe.to("cuda")
    pipe.enable_vae_slicing()
    pipe.enable_vae_tiling()
    return pipe
