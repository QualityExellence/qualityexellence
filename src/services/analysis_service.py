import os
import json
import nltk
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
from nltk.probability import FreqDist
from collections import Counter
import numpy as np
import openai
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configurar API key da OpenAI
openai.api_key = os.getenv('OPENAI_API_KEY')

# Baixar recursos do NLTK necessários
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

class TextAnalyzer:
    """
    Classe para análise e processamento de texto de transcrições.
    """
    
    def __init__(self, language='portuguese'):
        self.language = language
        self.stop_words = set(stopwords.words(language))
    
    def generate_summary(self, text, max_sentences=3):
        """
        Gera um resumo automático do texto.
        
        Args:
            text (str): Texto completo para resumir
            max_sentences (int): Número máximo de frases no resumo
            
        Returns:
            str: Resumo do texto
        """
        try:
            # Em produção, usaríamos a API da OpenAI para resumo
            # client = openai.OpenAI()
            # response = client.chat.completions.create(
            #     model="gpt-3.5-turbo",
            #     messages=[
            #         {"role": "system", "content": "Você é um assistente especializado em resumir transcrições de chamadas de atendimento ao cliente."},
            #         {"role": "user", "content": f"Resuma o seguinte texto em até {max_sentences} frases:\n\n{text}"}
            #     ],
            #     max_tokens=150
            # )
            # return response.choices[0].message.content.strip()
            
            # Para desenvolvimento, usamos uma abordagem simples de extração
            sentences = sent_tokenize(text)
            
            if len(sentences) <= max_sentences:
                return text
            
            # Abordagem simples: pegar as primeiras frases
            summary = ' '.join(sentences[:max_sentences])
            
            return summary
            
        except Exception as e:
            print(f"Erro ao gerar resumo: {str(e)}")
            # Fallback: retornar as primeiras frases
            sentences = sent_tokenize(text)
            return ' '.join(sentences[:max_sentences])
    
    def extract_keywords(self, text, top_n=20):
        """
        Extrai palavras-chave do texto com contagem e frequência.
        
        Args:
            text (str): Texto para análise
            top_n (int): Número de palavras-chave a retornar
            
        Returns:
            list: Lista de dicionários com palavras-chave, contagem e frequência
        """
        try:
            # Tokenizar e limpar o texto
            words = word_tokenize(text.lower())
            filtered_words = [word for word in words if word.isalpha() and word not in self.stop_words and len(word) > 3]
            
            # Contar frequência
            word_counts = Counter(filtered_words)
            total_words = len(filtered_words)
            
            # Formatar resultado
            keywords = []
            for word, count in word_counts.most_common(top_n):
                keywords.append({
                    'word': word,
                    'count': count,
                    'frequency': count/total_words if total_words > 0 else 0
                })
            
            return keywords
            
        except Exception as e:
            print(f"Erro ao extrair palavras-chave: {str(e)}")
            return []
    
    def calculate_tma(self, segments):
        """
        Calcula o Tempo Médio de Atendimento (TMA) com base nos segmentos.
        
        Args:
            segments (list): Lista de segmentos com timestamps
            
        Returns:
            float: TMA em segundos
        """
        try:
            if not segments:
                return 0
            
            # Tempo total da gravação (último timestamp de fim)
            total_time = segments[-1].get('end', 0)
            
            return total_time
            
        except Exception as e:
            print(f"Erro ao calcular TMA: {str(e)}")
            return 0
    
    def analyze_sentiment(self, text):
        """
        Analisa o sentimento do texto.
        
        Args:
            text (str): Texto para análise
            
        Returns:
            dict: Resultado da análise com score e classificação
        """
        try:
            # Em produção, usaríamos a API da OpenAI para análise de sentimento
            # client = openai.OpenAI()
            # response = client.chat.completions.create(
            #     model="gpt-3.5-turbo",
            #     messages=[
            #         {"role": "system", "content": "Você é um assistente especializado em análise de sentimento."},
            #         {"role": "user", "content": f"Analise o sentimento do seguinte texto e retorne um valor entre -1 (muito negativo) e 1 (muito positivo):\n\n{text}"}
            #     ],
            #     max_tokens=10
            # )
            # score = float(response.choices[0].message.content.strip())
            
            # Para desenvolvimento, usamos uma análise simples baseada em palavras-chave
            text = text.lower()
            
            # Palavras positivas e negativas para análise simples
            positive_words = ['bom', 'ótimo', 'excelente', 'satisfeito', 'feliz', 'grato', 'obrigado', 'agradeço', 'resolvido', 'solução']
            negative_words = ['ruim', 'péssimo', 'insatisfeito', 'problema', 'reclamação', 'erro', 'falha', 'dificuldade', 'demora', 'frustrado']
            
            # Contar ocorrências
            positive_count = sum(1 for word in positive_words if word in text)
            negative_count = sum(1 for word in negative_words if word in text)
            
            # Calcular score
            total = positive_count + negative_count
            if total == 0:
                score = 0
            else:
                score = (positive_count - negative_count) / total
            
            # Determinar classificação
            if score > 0.3:
                sentiment = 'positive'
            elif score < -0.3:
                sentiment = 'negative'
            else:
                sentiment = 'neutral'
            
            return {
                'score': score,
                'sentiment': sentiment,
                'is_critical': score < -0.5  # Momento crítico se muito negativo
            }
            
        except Exception as e:
            print(f"Erro ao analisar sentimento: {str(e)}")
            return {'score': 0, 'sentiment': 'neutral', 'is_critical': False}
    
    def detect_interruptions(self, segments, min_gap=0.3):
        """
        Detecta interrupções entre segmentos de fala.
        
        Args:
            segments (list): Lista de segmentos com timestamps e falantes
            min_gap (float): Intervalo mínimo entre segmentos para considerar uma interrupção
            
        Returns:
            list: Lista de interrupções detectadas
        """
        try:
            interruptions = []
            
            for i in range(1, len(segments)):
                prev_segment = segments[i-1]
                curr_segment = segments[i]
                
                # Verificar se há sobreposição ou gap muito pequeno
                if prev_segment['end'] > curr_segment['start'] or \
                   (curr_segment['start'] - prev_segment['end']) < min_gap:
                    
                    # Verificar se são falantes diferentes
                    if prev_segment.get('speaker') != curr_segment.get('speaker'):
                        interruptions.append({
                            'time': curr_segment['start'],
                            'interrupter': curr_segment.get('speaker', 'unknown'),
                            'interrupted': prev_segment.get('speaker', 'unknown'),
                            'text': curr_segment.get('text', '')
                        })
            
            return interruptions
            
        except Exception as e:
            print(f"Erro ao detectar interrupções: {str(e)}")
            return []
    
    def detect_long_pauses(self, segments, threshold=3.0):
        """
        Detecta pausas longas entre segmentos de fala.
        
        Args:
            segments (list): Lista de segmentos com timestamps
            threshold (float): Duração mínima em segundos para considerar uma pausa longa
            
        Returns:
            list: Lista de pausas longas detectadas
        """
        try:
            long_pauses = []
            
            for i in range(1, len(segments)):
                prev_segment = segments[i-1]
                curr_segment = segments[i]
                
                # Calcular duração da pausa
                pause_duration = curr_segment['start'] - prev_segment['end']
                
                # Verificar se é uma pausa longa
                if pause_duration >= threshold:
                    long_pauses.append({
                        'start_time': prev_segment['end'],
                        'end_time': curr_segment['start'],
                        'duration': pause_duration,
                        'prev_speaker': prev_segment.get('speaker', 'unknown'),
                        'next_speaker': curr_segment.get('speaker', 'unknown')
                    })
            
            return long_pauses
            
        except Exception as e:
            print(f"Erro ao detectar pausas longas: {str(e)}")
            return []
    
    def detect_critical_moments(self, segments):
        """
        Detecta momentos críticos na conversa com base em sentimento e interrupções.
        
        Args:
            segments (list): Lista de segmentos com texto e timestamps
            
        Returns:
            list: Lista de momentos críticos detectados
        """
        try:
            critical_moments = []
            
            for i, segment in enumerate(segments):
                text = segment.get('text', '')
                
                # Analisar sentimento do segmento
                sentiment_result = self.analyze_sentiment(text)
                
                # Verificar se é um momento crítico
                if sentiment_result['is_critical']:
                    critical_moments.append({
                        'time': segment['start'],
                        'end_time': segment['end'],
                        'speaker': segment.get('speaker', 'unknown'),
                        'text': text,
                        'sentiment_score': sentiment_result['score'],
                        'reason': 'negative_sentiment'
                    })
                
                # Verificar palavras de alerta
                alert_words = ['cancelar', 'reclamar', 'insatisfeito', 'problema', 'erro', 'falha', 'urgente', 'imediato']
                if any(word in text.lower() for word in alert_words):
                    critical_moments.append({
                        'time': segment['start'],
                        'end_time': segment['end'],
                        'speaker': segment.get('speaker', 'unknown'),
                        'text': text,
                        'reason': 'alert_words'
                    })
            
            # Detectar interrupções
            interruptions = self.detect_interruptions(segments)
            for interruption in interruptions:
                # Verificar se a interrupção é do cliente
                if 'cliente' in interruption['interrupter'].lower():
                    critical_moments.append({
                        'time': interruption['time'],
                        'speaker': interruption['interrupter'],
                        'text': interruption['text'],
                        'reason': 'customer_interruption'
                    })
            
            return critical_moments
            
        except Exception as e:
            print(f"Erro ao detectar momentos críticos: {str(e)}")
            return []
