from typing import Dict, List

import torch
from transformers import GenerationConfig, LlamaForCausalLM, LlamaTokenizer

DEFAULT_SYSTEM_PROMPT = """\
You are a helpful, respectful and honest assistant. Always answer as helpfully as possible, while being safe.  Your answers should not include any harmful, unethical, racist, sexist, toxic, dangerous, or illegal content. Please ensure that your responses are socially unbiased and positive in nature.

If a question does not make any sense, or is not factually coherent, explain why instead of answering something not correct. If you don't know the answer to a question, please don't share false information."""

B_INST, E_INST = "[INST]", "[/INST]"
B_SYS, E_SYS = "<<SYS>>\n", "\n<</SYS>>\n\n"

class Model:
    def __init__(self, **kwargs) -> None:
        self._data_dir = kwargs["data_dir"]
        self._config = kwargs["config"]
        self._secrets = kwargs["secrets"]
        self._model = None
        self._tokenizer = None

    def load(self):
        self._model = LlamaForCausalLM.from_pretrained(
            "meta-llama/Llama-2-7b-chat-hf", 
            use_auth_token=self._secrets["hf_api_key"], 
            device_map="auto"
        )
        self._tokenizer = LlamaTokenizer.from_pretrained(
            "meta-llama/Llama-2-7b-chat-hf", 
            use_auth_token=self._secrets["hf_api_key"]
        )

    def preprocess(self, request: Dict) -> Dict:
        """
        Incorporate pre-processing required by the model if desired here.

        These might be feature transformations that are tightly coupled to the model.
        """
        return request

    def postprocess(self, request: Dict) -> Dict:
        """
        Incorporate post-processing required by the model if desired here.
        """
        return request

    def forward(self, prompt, temperature=0.1, top_p=0.75, top_k=40, num_beams=1, **kwargs):
        prompt_wrapped = f"{B_INST} {B_SYS} {DEFAULT_SYSTEM_PROMPT} {E_SYS} {prompt} {E_INST}"
        
        inputs = self._tokenizer(
            prompt_wrapped, return_tensors="pt", truncation=True, padding=False, max_length=1056
        )
        input_ids = inputs["input_ids"].to("cuda")
        generation_config = GenerationConfig(
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            num_beams=num_beams,
            repetition_penalty=1.2,
            **kwargs,
        )
        with torch.no_grad():
            generation_output = self._model.generate(
                input_ids=input_ids,
                generation_config=generation_config,
                return_dict_in_generate=True,
                output_scores=True,
                max_length=512,
                early_stopping=True,
            )

        decoded_output = []
        for beam in generation_output.sequences:
            decoded_output.append(self._tokenizer.decode(beam, skip_special_tokens=True).replace(prompt_wrapped, ""))

        return decoded_output


    def predict(self, request: Dict) -> Dict[str, List]:
        prompt = request.pop("prompt")
        try:
            completions = self.forward(prompt, **request)
        except Exception as exc:
            return {"status": "error", "data": None, "message": str(exc)}

        return {"status": "success", "data": completions, "message": None}