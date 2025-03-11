import os
from configobj import ConfigObj
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain_groq import ChatGroq
from openai import OpenAI
from langchain_core.runnables import Runnable

# Load environment variables from .env
load_dotenv()

class LLMManager:
    def __init__(self, config_path='config.ini'):
        self.config = self.load_config(config_path)
        self.DEFAULT_FALLBACK_ORDER = ['openrouter', 'groq', 'ollama']

    def load_config(self, config_path):
        try:
            config = ConfigObj(config_path)
            if not config:
                raise ValueError("Config file is empty or not found")
            return config
        except Exception as e:
            raise Exception(f"Failed to load {config_path}: {e}")

    def setup_llm_with_fallback(self, fallback_order=None):
        if fallback_order is None:
            fallback_order = self.DEFAULT_FALLBACK_ORDER
        
        llm_instances = {}
        for source in fallback_order:
            try:
                cfg = self.config[f'llms_{source}']
                if source == 'openrouter':
                    api_key = os.getenv('OPENROUTER_API_KEY')
                    if not api_key:
                        raise ValueError("OPENROUTER_API_KEY not found")
                    client = OpenAI(
                        base_url="https://openrouter.ai/api/v1",
                        api_key=api_key,
                    )
                    llm_instances[source] = OpenRouterLLM(
                        client=client,
                        model=cfg['model'],
                        temperature=cfg['temperature'],
                        site_url=cfg['site_url'],
                        site_name=cfg['site_name']
                    )
                elif source == 'groq':
                    api_key = os.getenv('GROQ_API_KEY')
                    if not api_key:
                        raise ValueError("GROQ_API_KEY not found")
                    llm_instances[source] = ChatGroq(
                        model=cfg['model'],
                        temperature=float(cfg['temperature']),
                        api_key=api_key
                    )
                elif source == 'ollama':
                    llm_instances[source] = ChatOllama(
                        model=cfg['model'],
                        temperature=float(cfg['temperature'])
                    )
                else:
                    print(f"Unsupported LLM source in fallback: {source}")
                    continue
            except Exception as e:
                print(f"Failed to setup {source}: {e}")
                continue
        if not llm_instances:
            raise Exception("No LLMs could be set up from the fallback order.")
        return llm_instances

    def invoke_with_fallback(self, llm_instances, fallback_order, input_data):
        for source in fallback_order:
            if source in llm_instances:
                try:
                    result = llm_instances[source].invoke(input_data)
                    if hasattr(result, 'content'):  # For AIMessage from Groq/Ollama
                        result = result.content
                    if not isinstance(result, str):
                        raise ValueError(f"Unexpected result type from {source}: {type(result)}")
                    print(f"Successfully used {source} LLM.")
                    return result
                except Exception as e:
                    print(f"Failed with {source}: {e}. Falling back to next LLM.")
                    continue
        return "Error: All LLMs in fallback chain failed."

class OpenRouterLLM(Runnable):
    def __init__(self, client, model, temperature, site_url, site_name):
        super().__init__()
        self.client = client
        self.model = model
        self.temperature = temperature
        self.site_url = site_url
        self.site_name = site_name

    def invoke(self, input, config=None):
        prompt = str(input)
        try:
            completion = self.client.chat.completions.create(
                extra_headers={"HTTP-Referer": self.site_url, "X-Title": self.site_name},
                extra_body={},
                model=self.model,
                temperature=float(self.temperature),
                messages=[{"role": "user", "content": prompt}]
            )
            result = completion.choices[0].message.content
            if not result:
                raise ValueError("LLM returned an empty response")
            return result
        except Exception as e:
            print(f"Error during OpenRouter invocation: {e}")
            raise