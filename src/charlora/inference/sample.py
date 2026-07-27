import torch


def generate_image(pipe, prompt, negative_prompt = "", steps = 40, guidance_scale = 3.0, seed = 0):
  gen = torch.Generator("cuda").manual_seed(seed)
  generated_image = pipe(prompt = prompt, negative_prompt = negative_prompt, num_inference_steps = steps, guidance_scale = guidance_scale, generator = gen)
  return generated_image.images[0]