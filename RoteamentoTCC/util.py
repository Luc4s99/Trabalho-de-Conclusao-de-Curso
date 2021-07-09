# Arquivo com métodos úteis para a aplicação
# Biblioteca para leitura do arquivo OSM
import xml.etree.cElementTree as ET
# Classe que define um ponto no mapa
from Ponto import *
# Classe que define uma rua no mapa
from Rua import *


def __init__(self, primeiro_vertice, ultimo_vertice):
    pass


# Cria a população com um determinado número de individuos
def inicia_populacao(self, tam_populacao):
    pass


# Cria um único indivíduo
def cria_individuo(self):
    pass


# Realiza a leitura do arquivo de entrada
def le_arquivo(arquivo_entrada: str):

    # Criando uma instância para leitura do XML que foi passado como parâmetro
    arvore = ET.parse(arquivo_entrada)
    # Obtém a tag raiz do arquivo
    raiz = arvore.getroot()

    # Lista de itens que serão removidos, esses itens não são interessantes para o trabalho
    # Ex: Rios, ferrovias, montanhas, morros, sinais de trânsito, estabelecimentos
    remover = ['traffic_signals', 'place_of_worship', 'church', 'supermarket', 'educational_institution', 'school',
               'hospital', 'atm', 'bakery', 'bank', 'pharmacy', 'bus_station', 'hotel', 'convenience', 'taxi',
               'restaurant', 'library', 'police', 'furniture', 'sports_centre', 'tower', 'fast_food', 'peak', 'river',
               'rail']

    # Armazena as tags que serão retiradas
    limpar = []

    # Armazena em um dicionario os pontos que foram mapeados na leitura do arquivo
    pontos = {}

    # Armazena em um dicionario as ruas que foram mapeadas na leitura do arquivo
    ruas = {}

    # Percorre todos as tags filhas da tag raiz
    for ramo in raiz:

        # Se a tag do ramo for um nó, possui informações a serem tratadas
        if ramo.tag == 'node':

            # Variável que indica se aquele nó foi removido
            isremovida = False

            # Percorre todas as tags filhas da tag ramo
            for filha_ramo in ramo:

                # Se alguma filha possuir a tag 'tag'
                if filha_ramo.tag == 'tag':

                    # Obtém o valor do atributo 'v' dessa tag
                    v = filha_ramo.get('v')

                    # Se contiver alguma informação da lista de remoção, esse nó será retirado
                    if v in remover:

                        # Verifica se o ramo já não foi colocado na lista
                        if ramo not in limpar:
                            limpar.append(ramo)
                            isremovida = True

            # Se aquele nó não será removido, então ele é mapeado
            if not isremovida:
                ponto = Ponto()

                # Obtém o id do nó, latitude e longitude
                ponto.set_id(ramo.get('id'))
                ponto.set_latitude(ramo.get('lat'))
                ponto.set_longitude((ramo.get('lon')))

                # Insere no dicionário de pontos
                pontos[ramo.get('id')] = ponto

        # Se o ramo for um caminho, possui informação a ser tratada
        elif ramo.tag == 'way':

            # Guardando o id da rua
            id_rua = ramo.get('id')

            # Instancia uma rua
            rua = Rua()

            # Identifica se aquela tag será retirada
            isremovida = False

            # Obtém o id da rua, latitude e longitude
            rua.set_id(id_rua)
            rua.set_latitude(ramo.get('lat'))
            rua.set_longitude((ramo.get('lon')))

            # Percorre todas as tags filhas da tag ramo
            for filha_ramo in ramo:

                # Tag que possui as informações dos nós que formam a rua
                if filha_ramo.tag == 'nd':

                    # Pega a referencia do nó
                    ref = filha_ramo.get('ref')

                    # Verifica se o nó existe na lista de nós
                    if ref in pontos.keys():

                        # Insere na lista de nós da rua
                        # O ponto é buscado na lista de pontos com base na chave, que é seu id
                        rua.insere_ponto(pontos[ref])

                # Se alguma filha possuir a tag 'tag'
                elif filha_ramo.tag == 'tag':

                    # Obtém o valor do atributo 'v' dessa tag
                    v = filha_ramo.get('v')

                    # Se contiver alguma informação da lista de remoção, esse nó será retirado
                    if v in remover:

                        # Marca a tag para ser removida
                        isremovida = True

            # Se a tag estiver marcada, ela é colocada na lista de limpeza
            if isremovida:

                # Se o ramo já não estiver na lista de limpeza, ele é adicionado
                if ramo not in limpar:
                    limpar.append(ramo)

            # Senão a rua é inserida no dicionário de ruas
            else:

                # Define a chave(id da rua) e insere no dicionário
                ruas[id_rua] = rua

    # Retira as tags do documento
    for item in limpar:
        raiz.remove(item)

    # Cria um documento de saída mais enxuto, sem tag que não serão utilizadas
    arvore.write('saida.osm')
