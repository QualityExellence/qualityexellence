import os
import json
import logging
from datetime import datetime
from dotenv import load_dotenv

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WhisperService:
    """
    Serviço para transcrição de áudio usando a API Whisper da OpenAI
    Compatível com múltiplas versões da biblioteca OpenAI
    """

    def __init__(self):
        """
        Inicializa o serviço Whisper com compatibilidade para diferentes versões da API OpenAI
        """
        # Obter chave da API do ambiente
        self.api_key = os.getenv('OPENAI_API_KEY')
        logger.info(f"API Key detectada: {self.api_key[:5]}..." if self.api_key else "API Key não encontrada")
        self.client = None

        # Verificar se a chave da API está disponível
        if not self.api_key:
            logger.warning("Chave da API OpenAI não encontrada. Usando modo simulado.")
            return

        # Tentar inicializar o cliente OpenAI usando diferentes métodos
        # para compatibilidade com diferentes versões da biblioteca
        try:
            # Método 1: Tentar importar o módulo openai
            import openai

            # Configurar a chave da API
            openai.api_key = self.api_key

            # Tentar usar a nova API (versão >= 1.0.0)
            try:
                # Importar diretamente do módulo
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key)
                self.api_version = "new"
                logger.info("Usando API OpenAI versão >= 1.0.0")
            except (ImportError, AttributeError, TypeError):
                # Se falhar, tentar a API antiga (versão < 1.0.0)
                try:
                    # Verificar se o módulo openai tem o atributo Completion
                    if hasattr(openai, 'Completion'):
                        self.client = openai
                        self.api_version = "old"
                        logger.info("Usando API OpenAI versão < 1.0.0")
                    else:
                        raise ImportError("Módulo OpenAI não tem os atributos esperados")
                except Exception as e:
                    logger.error(f"Erro ao inicializar cliente OpenAI (modo antigo): {str(e)}")
                    self.client = None
        except ImportError:
            logger.error("Módulo OpenAI não encontrado. Usando modo simulado.")
            self.client = None

    def transcribe_audio(self, file_path, language=None, diarization=False):
        """
        Transcreve um arquivo de áudio usando a API Whisper

        Args:
            file_path (str): Caminho do arquivo de áudio
            language (str, optional): Código do idioma (ex: 'pt', 'en'). Se None, detecta automaticamente.
            diarization (bool, optional): Se True, tenta identificar diferentes falantes

        Returns:
            dict: Resultado da transcrição com texto, segmentos, idioma detectado, etc.
        """
        # Verificar se o arquivo existe
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

        # Verificar se temos acesso à API
        if not self.client:
            logger.info("Usando transcrição simulada (modo de desenvolvimento)")
            return self._simulate_transcription(file_path, language, diarization)

        try:
            # Abrir o arquivo de áudio
            with open(file_path, "rb") as audio_file:
                # Chamar a API Whisper usando a versão apropriada da API
                if hasattr(self, 'api_version') and self.api_version == "new":
                    # Nova API (versão >= 1.0.0)
                    response = self.client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        language=language,
                        response_format="verbose_json"
                    )

                    # Processar resposta
                    if isinstance(response, dict):
                        # Resposta já é um dicionário
                        result = response
                    else:
                        # Converter resposta para dicionário
                        try:
                            result = response.model_dump()
                        except AttributeError:
                            # Fallback se model_dump não estiver disponível
                            result = response.__dict__
                else:
                    # API antiga (versão < 1.0.0)
                    response = self.client.Audio.transcribe(
                        model="whisper-1",
                        file=audio_file,
                        language=language,
                        response_format="verbose_json"
                    )
                    result = response

                # Adicionar informações adicionais
                result['language'] = result.get('language', language or 'auto')

                # Processar segmentos para adicionar identificação de falantes se solicitado
                if diarization and 'segments' in result:
                    result['segments'] = self._add_speaker_diarization(result['segments'])

                return result

        except Exception as e:
            logger.error(f"Erro ao transcrever áudio: {str(e)}")
            # Em caso de erro, retornar transcrição simulada
            logger.info("Usando transcrição simulada devido a erro na API")
            return self._simulate_transcription(file_path, language, diarization)

    def _add_speaker_diarization(self, segments):
        """
        Adiciona identificação de falantes aos segmentos
        Nota: Em uma implementação real, usaríamos um modelo de diarização

        Args:
            segments (list): Lista de segmentos da transcrição

        Returns:
            list: Segmentos com identificação de falantes
        """
        # Simular identificação de falantes
        # Em uma implementação real, usaríamos um modelo como pyannote.audio

        current_speaker = "Speaker A"
        for i, segment in enumerate(segments):
            # Alternar entre falantes a cada 2-3 segmentos
            if i > 0 and i % 2 == 0:
                current_speaker = "Speaker B" if current_speaker == "Speaker A" else "Speaker A"

            # Adicionar identificação de falante
            segment['speaker'] = current_speaker

            # Adicionar sentimento (simulado)
            # Em uma implementação real, usaríamos análise de sentimento
            segment['sentiment'] = 0.0  # Neutro

        return segments

    def _simulate_transcription(self, file_path, language=None, diarization=False):
        """
        Simula uma transcrição para desenvolvimento e testes

        Args:
            file_path (str): Caminho do arquivo de áudio
            language (str, optional): Código do idioma
            diarization (bool, optional): Se True, adiciona identificação de falantes

        Returns:
            dict: Transcrição simulada
        """
        # Obter nome do arquivo sem extensão
        filename = os.path.basename(file_path)
        name_without_ext = os.path.splitext(filename)[0]

        # Gerar texto simulado baseado no nome do arquivo
        simulated_text = f"Esta é uma transcrição simulada para o arquivo {name_without_ext}. "
        simulated_text += "O serviço está funcionando em modo de desenvolvimento sem acesso à API OpenAI. "
        simulated_text += "Para transcrições reais, configure a chave da API OpenAI no arquivo .env."

        # Gerar segmentos simulados
        segments = []
        words = simulated_text.split()
        segment_size = min(20, len(words))  # Tamanho do segmento (em palavras)

        for i in range(0, len(words), segment_size):
            segment_words = words[i:i+segment_size]
            segment_text = " ".join(segment_words)

            segment = {
                'id': i // segment_size,
                'start': i // segment_size * 5.0,  # 5 segundos por segmento
                'end': (i // segment_size + 1) * 5.0,
                'text': segment_text,
                'words': [{'word': word, 'start': i // segment_size * 5.0 + j * 0.5, 'end': i // segment_size * 5.0 + j * 0.5 + 0.4} for j, word in enumerate(segment_words)]
            }

            segments.append(segment)

        # Adicionar identificação de falantes se solicitado
        if diarization:
            segments = self._add_speaker_diarization(segments)

        # Construir resultado
        result = {
            'text': simulated_text,
            'segments': segments,
            'language': language or 'pt',
            'is_simulated': True
        }

        return result
