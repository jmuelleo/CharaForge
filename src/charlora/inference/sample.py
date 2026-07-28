import torch


def generate_image(pipe, prompt, negative_prompt = "", steps = 40, guidance_scale = 3.0, seed = 0):
  gen = torch.Generator("cuda").manual_seed(seed)
  latents = pipe(prompt = prompt, negative_prompt = negative_prompt, num_inference_steps = steps, guidance_scale = guidance_scale, generator = gen, output_type = "latent").images
  latents = pipe._unpack_latents(latents, 1024, 1024, pipe.vae_scale_factor)
  latents = latents.to(torch.float32)
  latents = (latents / pipe.vae.config.scaling_factor) + pipe.vae.config.shift_factor
  generated_image = pipe.vae.decode(latents, return_dict = False)[0]
  generated_image = pipe.image_processor.postprocess(generated_image, output_type = "pil")
  return generated_image[0]