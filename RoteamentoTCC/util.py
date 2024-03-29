"""

Este código possui partes desenvolvidas ou baseadas em código desenvolvido por Saulo Ricardo
Link do GitHub: https://github.com/SauloRicardo/TCC_Final

E também possui partes desenvolvidas e baseadas em código desenvolvido por Mateus Soares
Link do GitHub: https://github.com/MateusSoares/Wireless-Access-Point-Optimization

Este projeto também utiliza dados obtidos pelo projeto Open Street Map
Link: https://www.openstreetmap.org/about
"""

# Arquivo com métodos úteis para a aplicação
# Biblioteca para leitura do arquivo OSM
import os
import random
import xml.etree.cElementTree as ET
# Biblioteca para plotagem de dados no google maps
import gmplot
# Classe que define um ponto no mapa
from RoteamentoTCC.Ponto import *
# Classe que define uma rua no mapa
from RoteamentoTCC.Rua import *
# Biblioteca que realiza operações com grafos
import networkx as nx
# Biblioteca para cálculos utilizando coordenadas geográficas
import geopy.distance
# Biblioteca para plotagem de gráficos e dados em geral
from matplotlib import pyplot as plt
# Biblioteca que contém úteis matemáticos
import numpy as np
# Biblioteca para a realização do agrupamento dos pontos
from sklearn.cluster import KMeans
# Biblioteca para limpeza de lixo de memória(garbage collector)
import gc
# Classe que define e executa o Non-dominated Sorting Genetic Algorithm II
from RoteamentoTCC.nsga.nsga2 import NSGA2
# Bibliotecas para criação de arquivos temporários
import tempfile
import shutil
# Função de arredondamento para cima
from math import ceil
# Bibliotecas necessárias para capturar a altitude dos pontos
import requests
import time

# Número máximo de clusters
MAX_CLUSTERS = 30
# MAX_CLUSTERS = 3

# Número máximo de caminhões
MAX_CAMINHOES = 30

# Indica qual mapa está sendo usado: F = Formiga; L = Lagoa da Prata
# MAPA = 'F'
MAPA = 'L'

# Parâmetros para a plotagem de imagens
plt.rcParams['figure.figsize'] = (16, 9)
plt.style.use('ggplot')

# Armazena em um dicionario os pontos que foram mapeados na leitura do arquivo
pontos = {}

# Dicionário que armazena os pontos que restaram depois da otimização do grafo
pontos_otimizados = {}

# Armazena em um dicionario as ruas que foram mapeadas na leitura do arquivo
ruas = {}

# Grafo que representa o mapa completo da cidade
grafo_cidade = nx.Graph()

# Grafo que será utilizado para representar o mapa da cidade já simplificado
grafo_cidade_simplificado = nx.MultiGraph()

# Capacidade de lixo que um caminhão de lixo possuiem KG
CAPACIDADE_CAMINHAO = 10000
# CAPACIDADE_CAMINHAO = 1000

# Identifica o id do ponto que representa o depósito no mapa de Lagoa da Prata - MG
DEPOSITO = '353304393'
# Identifica o id do ponto que representa o depósito no mapa de Formiga - MG
# DEPOSITO = '3627233002'
# Identificador do depósito no arquivo utilizado para testes
# DEPOSITO = '7560818573'

# ID's de pontos que serão retirados "manualmente" para que o NSGA-II seja melhor calibrado
pontos_retirar_manual = ['2386701666', '2386701653', '353461444', '8256516317', '1344105186', '2386701633',
                         '7105572020', '8405717762', '5420412669', '353460735', '1344104828', '1826545975',
                         '4055552318', '5420412934', '7802750044', '3545678179', '4055552327', '7872173741']

# Quantidade total de lixo que foi gerada na cidade
quantidade_lixo_cidade = 0

# Dicionário que armazena um 'cache' dos mapas que podem ser gerados pelo k-means
# Utilizado para poupar tempo ao rodar o algoritmo
cache_mapas_eulerizados = {}


def __init__():
    pass


# Realiza a leitura do arquivo de entrada
def le_arquivo(arquivo_entrada: str):
    # Criando uma instância para leitura do XML que foi passado como parâmetro
    arvore = ET.parse(arquivo_entrada)
    # Obtém a tag raiz do arquivo
    raiz = arvore.getroot()
    # Referencias de nós de caminhos para serem removidos
    referencias_nos = []

    # ID's de ruas que serão retiradas "manualmente" para que o grafo fique melhor organizado
    ruas_retirar_manual = ['171661658', '837763522', '844146081', '119717353', '835715874']

    # Lista de itens que serão removidos, esses itens não são interessantes para o trabalho
    # Ex: Rios, ferrovias, montanhas, morros, sinais de trânsito, estabelecimentos
    remover = ['traffic_signals', 'place_of_worship', 'church', 'supermarket', 'educational_institution', 'school',
               'hospital', 'atm', 'bakery', 'bank', 'pharmacy', 'bus_station', 'hotel', 'convenience', 'taxi',
               'restaurant', 'library', 'police', 'furniture', 'sports_centre', 'tower', 'fast_food', 'peak', 'river',
               'rail', 'wood', 'statue', 'clothes', 'fuel', 'gate', 'cattle_grid', 'track', 'path', 'water', 'unpaved']

    # Armazena as tags que serão retiradas
    limpar = []

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
                ponto.id = ramo.get('id')
                ponto.latitude = ramo.get('lat')
                ponto.longitude = (ramo.get('lon'))

                # Insere no dicionário de pontos
                pontos[ramo.get('id')] = ponto

        # Se o ramo for um caminho, possui informação a ser tratada
        elif ramo.tag == 'way':

            # Guardando o id da rua
            id_rua = ramo.get('id')

            # Identifica se aquela tag será retirada
            isremovida = False

            # Lista auxiliar para nós dos caminhos
            aux_ref = []

            # Percorre todas as tags filhas da tag ramo
            for filha_ramo in ramo:

                # Tag que possui as informações dos nós que formam a rua
                if filha_ramo.tag == 'nd':

                    # Insere o nó na lista auxiliar de referências daquele caminho
                    aux_ref.append(filha_ramo.get('ref'))

                # Se alguma filha possuir a tag 'tag'
                elif filha_ramo.tag == 'tag':

                    # Obtém o valor do atributo 'v' dessa tag
                    v = filha_ramo.get('v')

                    # Se contiver alguma informação da lista de remoção, esse nó será retirado
                    if v in remover or id_rua in ruas_retirar_manual:
                        # Marca a tag para ser removida
                        isremovida = True

            # Se a tag estiver marcada, ela é colocada na lista de limpeza
            if isremovida:

                # Nós da lista de referencia são passados para a lista final
                for no in aux_ref:
                    referencias_nos.append(no)

                # Se o ramo já não estiver na lista de limpeza, ele é adicionado
                if ramo not in limpar:
                    limpar.append(ramo)

            # Senão a rua é inserida no dicionário de ruas
            else:

                # Instancia uma rua
                rua = Rua()

                # Seta o id da rua
                rua.id = id_rua

                # Percorre os nós daquele caminho
                for ref in aux_ref:

                    # Verifica se o nó existe na lista de nós
                    if ref in pontos.keys():
                        # Insere na lista de nós da rua
                        # O ponto é buscado na lista de pontos com base na chave, que é seu id
                        rua.insere_ponto(pontos[ref])

                # Define a chave(id da rua) e insere no dicionário
                ruas[id_rua] = rua

    # Percorrendo o arquivo novamente retirando nós remanescentes
    for ramo in raiz:

        # Limpa as tags de caminhos que não serão utilizados
        if ramo.tag == 'node':

            # Se o id desse nó estiver nos nós remanescentes, ele será excluído
            if ramo.get('id') in referencias_nos:
                limpar.append(ramo)

        # Chegando as tags de caminhos, nada mais precisa ser verificado
        if ramo.tag == 'way':
            break

    # Verifica se alguma rua que não será retirada possui o nó analisado
    # Se existir tal rua, o nó não poderá ser retirado
    for _, rua in ruas.items():

        # O dicionário 'ruas' contém todas as ruas que serão utilizadas e já estão validadas
        # Então se o ponto estiver em uma dessas ruas ele já não pode ser retirado
        for rua_ponto in rua.pontos:

            # Passa por todos os nós da lista de limpeza, verificando se alguns deles compõe a rua
            for no_limpar in limpar:

                # Se identificar que algum nó está na rua
                if no_limpar.attrib['id'] == rua_ponto.id:
                    # Ele é retirado da lista de limpeza
                    limpar.remove(no_limpar)

    # Passa pela lista de pontos retirando os nós que serão limpos
    # Como a lista 'limpar' foi verificada acima, todos os pontos que estão nessa lista com certeza serão eliminados
    for no_limpar in limpar:

        # Verifica antes se esta analisando um nó
        if no_limpar.tag == 'node':

            # Retira dos pontos mapeados os nós de caminhos excluídos e que não serão utilizados em outros caminhos
            if pontos.__contains__(no_limpar.attrib['id']):
                pontos.pop(no_limpar.attrib['id'])

    # Retira as tags do documento
    for item in limpar:
        raiz.remove(item)

    # Cria um documento de saída mais enxuto, sem tags que não serão utilizadas
    arvore.write('saida/saida.osm')

    print("Arquivo de saída gerado!")


def otimiza_grafo():
    # Percorre todos os nós que já foram obtidos
    for id_ponto, ponto in pontos.items():

        # Inicializa um contador para o ponto, se o mesmo aparecer mais de uma vez durante a iteração das ruas ele tem
        # grandes chances de ser uma esquina
        contador_ponto = 0

        # Verifica antes se o ponto é um dos que deve ser retirado "manualmente"
        if id_ponto in pontos_retirar_manual:
            continue

        # Primeiramente verifica se o ponto é o final de uma rua, se for deve ser inserido
        # O ponto que possui somente um vizinho, é considerado um final de rua
        if len(ponto.pontos_vizinhos) == 1:
            pontos_otimizados[id_ponto] = ponto

        # Se o ponto não foi inserido acima, existem mais testes a serem realizados
        if not pontos_otimizados.__contains__(ponto):

            # Percorre todas as ruas, verificando se aquele ponto está contido nela
            for id_rua, rua in ruas.items():

                # Verifica cada um dos pontos da rua, se bate com o ponto sendo analisado atualmente
                for ponto_rua in rua.pontos:

                    # Verifica se o ponto é válido
                    if ponto_rua is not None and ponto_rua.id != -1:

                        # Verifica se o id dos pontos bate
                        if ponto_rua.id == id_ponto:
                            # Incrementa o contador, pois o ponto faz parte da rua
                            contador_ponto = contador_ponto + 1

                        # Verifica se o contador está maior que 1, o que indica que o ponto pode ser uma esquina
                        if contador_ponto > 1:
                            # Insere o ponto na lista de pontos otimizados
                            pontos_otimizados[id_ponto] = ponto

                            # Encerra o for, pois o ponto já está na lista de otimizados
                            break


def adiciona_alturas():

    # Abre o arquivo que contém as altitudes dos pontos
    if MAPA == 'F':

        arq_altitudes = open("entrada/alturas.osm", "r")
    else:

        arq_altitudes = open("entrada/alturas_lagoa.osm", "r")

    # Passa por todas as linhas do arquivo
    for linha in arq_altitudes:

        # Quebra as informações da linha em uma lista
        linha = linha.split()

        # Extrai o id e altitude do ponto em questão
        id = linha[2].replace("\"", "")
        alt = float(linha[5].replace("\"", ""))

        # Adiciona a altura ao respectivo ponto
        if pontos_otimizados.get(id) is not None:
            pontos_otimizados.get(id).altitude = alt

    # Fecha o arquivo já que  não será mais usado
    arq_altitudes.close()


# Função que faz a interligação dos pontos obtidos no mapa, forma as ruas e as plota
def mapeia_ruas(arquivo):
    lat = []
    lon = []

    tuplas_latlon = []

    # Obtem os pontos para serem plotados
    for id_pnt in pontos:

        tuplas_latlon.append((pontos[id_pnt].latitude, pontos[id_pnt].longitude))
        lat.append(pontos[id_pnt].latitude)
        lon.append(pontos[id_pnt].longitude)

    # Adiciona o local inicial a plotagem
    mapa_plot = gmplot.GoogleMapPlotter(lat[0], lon[0], 13)

    # Criando uma instância para leitura do XML que foi passado como parâmetro
    arvore = ET.parse(arquivo)
    # Obtém a tag raiz do arquivo
    raiz = arvore.getroot()

    # Começa a leitura das tags do arquivo
    for ramo in raiz:

        # Se a tag for um caminho, então ela será analisada
        if ramo.tag == 'way':

            # Realiza a instância de uma rua
            rua = Rua()

            # Usa o mesmo id da rua do arquivo de parâmetro na rua instanciada
            rua.id = ramo.get('id')

            # Lista de tuplas com latitudes e longitudes dos pontos das ruas
            tuplas_rua = []

            # Ponto que está sendo analisado
            ponto_atual = Ponto(gera_label=False)

            # Ponto anterior ao atual, usado para identificar vizinhos
            ponto_anterior = Ponto(gera_label=False)

            # Percorrendo todas as tags de atributo da tag atual
            for filha_ramo in ramo:

                # Se a tag atributo for do tipo nd (nó)
                # Ela possui a referencia de um dos nós que compõe a rua
                if filha_ramo.tag == 'nd':

                    # Verifica se esse nó existe
                    if pontos.__contains__(filha_ramo.get('ref')):

                        # Salva o ponto atual, e insere suas coordenadas na lista de tuplas
                        ponto_atual = pontos[filha_ramo.get('ref')]
                        tuplas_rua.append((float(ponto_atual.latitude), float(ponto_atual.longitude)))

                        # Insere o ponto na lista de pontos da rua
                        rua.insere_ponto(ponto_atual)

                        # Se o ponto anterior ao atual possuir algum id
                        # Significa que existe uma ligação de pontos a ser realizada
                        if ponto_anterior.id != -1:
                            # Informa que o ponto atual possui ligação com o ponto anterior
                            pontos[filha_ramo.get('ref')].realiza_ligacao(ponto_anterior)

                            # E consequentemente o ponto anterior possui ligação com o ponto atual
                            pontos[ponto_anterior.id].realiza_ligacao(ponto_atual)

                        ponto_anterior = ponto_atual

                # Identifica o atributo 'tag' da tag atual
                if filha_ramo.tag == 'tag':

                    # Identifica a chave nome, que indica o nome da rua e atribui a rua atual
                    if filha_ramo.get('k') == 'name':
                        rua.nome = filha_ramo.get('v')

            # Verifica se a rua possui ao menos um ponto em sua formação
            # Se possuir, ela é inserida no dicionário de ruas
            if len(rua.pontos) != 0:
                ruas[rua.id] = rua

            # Se existir algo na lista de tuplas, significa que existem dados a serem exibidos
            if len(tuplas_rua) != 0:
                # Adiciona ao mapa de plotagem as coordenadas das ruas
                rua_lat, rua_lon = zip(*tuplas_rua)
                mapa_plot.scatter(rua_lat, rua_lon, '#3B0B39', size=5, marker=False)
                mapa_plot.plot(rua_lat, rua_lon, 'cornflowerblue', edge_width=3)

    # Adiciona ao mapa de plotagem as coordenadas dos pontos e gera o arquivo
    draw_lat, draw_lon = zip(*tuplas_latlon)
    mapa_plot.scatter(draw_lat, draw_lon, '#3B0B39', size=5, marker=False)
    mapa_plot.draw('saida/mapa.html')


# Essa função atualiza os vizinhos dos pontos após a otimização do grafo
# Pois durante o processo de otimização, alguns vizinhos podem ter sido removidos
def atualiza_vizinhos():
    # Primeiro limpa todos os vizinhos dos pontos otimizados
    for ponto in pontos_otimizados.values():
        ponto.pontos_vizinhos.clear()

    # Então insere os vizinhos atualizados, com base nas arestas do grafo
    for tupla in grafo_cidade_simplificado.edges:
        pontos_otimizados[tupla[0]].pontos_vizinhos.append(pontos_otimizados[tupla[1]])
        pontos_otimizados[tupla[1]].pontos_vizinhos.append(pontos_otimizados[tupla[0]])


# Função que monta o grafo que representa o mapa e o plota
def monta_grafo_otimizado(pontos_grafo, nome_arquivo_saida):
    coordenadas_pontos = {}

    # Percorre todas as ruas do grafo
    for rua_id, rua in ruas.items():

        # Percorre cada um dos pontos que forma a rua
        for ponto_rua in rua.pontos:

            # Verifica se o ponto da rua que está sendo analisado é um ponto válido
            if ponto_rua.id in pontos_grafo.keys():

                # Esta variável indica qual o index do ponto que está sendo analisado
                index_ponto = rua.pontos.index(ponto_rua)

                # Insere cada um dos pontos no grafo para que sejam plotados
                grafo_cidade_simplificado.add_node(ponto_rua.id)

                # Percorre novamente todos os pontos que formam aquela rua
                for ponto_rua_ligar in rua.pontos:

                    # Porem só serão analisados pontos que estão a frente do ponto analisado atualmente
                    # E pontos válidos
                    if (rua.pontos.index(ponto_rua_ligar) > index_ponto) and (
                            ponto_rua_ligar.id in pontos_grafo.keys()):

                        # Se um ponto válido for encontrado para frente do que está sendo analisado
                        if ponto_rua_ligar.id in pontos_grafo.keys():
                            # Função que calcula a distância entre os pontos
                            distancia_pontos = calcula_distancia_real(rua_id, ponto_rua, ponto_rua_ligar)

                            # Insere a aresta no grafo
                            grafo_cidade_simplificado.add_edge(ponto_rua.id, ponto_rua_ligar.id,
                                                               weight=distancia_pontos, rua=rua)

                            # Para o for, pois a ligação desse ponto já foi encontrada
                            break

    # Armazena as coordenadas dos pontos para que seja realizada a plotagem
    for node in nx.nodes(grafo_cidade_simplificado):
        coordenadas_pontos[node] = pontos[node].retorna_coordenadas()

    # Desenha a figura e salva com o nome definido
    nx.draw(grafo_cidade_simplificado, node_size=0.5, node_color='grey', alpha=0.5, with_labels=False,
            pos=coordenadas_pontos)
    plt.savefig(nome_arquivo_saida, dpi=500)

    # Limpa a figura para evitar que o marplotlib se "lembre" da figura
    plt.clf()

    # Fecha a instância do pyplot para que nenhum lixo de memória seja inserido na próxima imagem
    plt.close()

    # Realiza a coleta de lixo de memória
    gc.collect()

    atualiza_vizinhos()


# Função que calcula a distância real entre dois pontos de uma rua
# A distância real neste caso, é a distância considerando todos os pontos da rua, até os pontos que foram retirados pela
# otimização
def calcula_distancia_real(rua_id, ponto_inicial, ponto_final):
    # Obtem a rua do dicionário de ruas
    rua = ruas[rua_id]

    # Inicia a variável que aramzena a distância total entre os pontos
    distancia_total_pts = 0

    # Indica que o ponto inicial foi encontrado e que as distâncias podem começar a serem somadas
    achou_ponto_inicial = False

    # Percorre todos os pontos da rua, até achar o ponto inicial
    for ponto_rua in rua.pontos:

        # Verifica se o ponto corresponde ao ponto inicial
        if ponto_rua.id == ponto_inicial.id:
            achou_ponto_inicial = True

        # Se o ponto inicial foi encontrado, as distâncias podem ser somadas
        if achou_ponto_inicial:

            # Vai adicionando as distâncias até o próximo ponto a distância total final
            distancia_total_pts += calcula_distancia_pontos(ponto_inicial.latitude, ponto_inicial.longitude,
                                                            ponto_rua.latitude, ponto_rua.longitude)

            # Se o ponto sendo analisado atualmente for o ponto final, então deve ser parada a iteração
            if ponto_rua.id == ponto_final.id:
                break

    # Adiciona o tamanho do segmento de rua calculado, ao total da rua
    # Ao final de todas as iteraçãoes dessa função, todas as ruas terão seus tamanhos totais já calculados
    rua.tamanho_rua += distancia_total_pts

    # Retorna a distância total
    return distancia_total_pts


# Função que monta o grafo que representa o mapa e o plota
def monta_grafo(nome_arquivo):

    coordenadas_pontos = {}

    # Percorre todos os pontos definidos
    for pnt in pontos:

        # Insere cada um dos pontos no grafo para que sejam plotados
        grafo_cidade.add_node(pontos[pnt].id)

        # Verifica cada vizinho de ponto para que sejam montadas as arestas
        for pnt_ligado in pontos[pnt].pontos_vizinhos:
            # Calcula a distância entre os pontos, que será utilizada como peso para a aresta
            distancia_pontos = calcula_distancia_pontos(pontos[pnt].latitude, pontos[pnt].longitude,
                                                        pnt_ligado.latitude, pnt_ligado.longitude)

            # Insere a aresta no grafo
            grafo_cidade.add_edge(pontos[pnt].id, pnt_ligado.id, weight=distancia_pontos)

    # Armazena as coordenadas dos pontos para que seja realizada a plotagem
    for node in nx.nodes(grafo_cidade):
        coordenadas_pontos[node] = pontos[node].retorna_coordenadas()

    # Desenha a figura e salva com o nome definido
    nx.draw(grafo_cidade, node_size=0.5, node_color='grey', alpha=0.5, with_labels=False, pos=coordenadas_pontos)
    plt.savefig(nome_arquivo, dpi=500)

    # Limpa a figura para evitar que o marplotlib se "lembre" da figura
    plt.clf()

    # Fecha a instância do pyplot para que nenhum lixo de memória seja inserido na próxima imagem
    plt.close()

    # Realiza a coleta de lixo de memória
    gc.collect()


def desenha_grafo(grafo):
    coordenadas_pontos = {}

    for node in nx.nodes(grafo):
        coordenadas_pontos[node] = pontos[node].retorna_coordenadas()

    nx.draw(grafo, node_size=0.5, node_color='grey', alpha=0.5, with_labels=False,
            pos=coordenadas_pontos)
    plt.savefig("saida/grafoDesenhado.png", dpi=500)

    # Limpa a figura para evitar que o marplotlib se "lembre" da figura
    plt.clf()

    # Fecha a instância do pyplot para que nenhum lixo de memória seja inserido na próxima imagem
    plt.close()

    # Realiza a coleta de lixo de memória
    gc.collect()


# Função que calcula a demanda aproximada de lixo de cada rua e divide entre seus pontos
def calcula_demandas(nome_arquivo):
    # Identifica a variável global que armazena a quantidade de lixo total gerada na cidade
    global quantidade_lixo_cidade

    # Passa por todas as ruas
    for _, rua in ruas.items():

        # Gera a demanda de lixo aproximada da rua
        # Para a geração da demanda utiliza a distribuição de Weibull, que é uma distribuição de cauda longa
        # O parâmetro 10 é o tamanho médio de lote de casa para a cidade analisada, logo o tamanho da rua / 10 resulta
        # no total de casas aproximado que aquela rua contém
        # Multiplicado por 2 pois os dois lados da rua possuem casas
        # Isso é multiplicado por 3 pois, a média de pessoas por família é de 3 e a média de produção de lixo por pessoa
        # é de 1kg
        rua.quantidade_lixo_rua = int((np.random.weibull(5.) * rua.tamanho_rua / 10) * 2) * 3

        # Divide de forma uniforme entre os pontos da rua a quantidade de lixo estimada
        qtd_lixo_ponto = rua.quantidade_lixo_rua / len(rua.pontos)

        # Percorre todos os pontos da rua atribuindo a quantidade de lixo
        for ponto in rua.pontos:

            # Se o ponto analisado for o próprio depósito, não será atribuída demanda de lixo para ele
            if ponto.id == DEPOSITO:
                continue

            ponto.quantidade_lixo = qtd_lixo_ponto

    coordenadas_pontos = {}

    # Armazena as coordenadas dos pontos para que seja realizada a plotagem
    for node in nx.nodes(grafo_cidade_simplificado):
        coordenadas_pontos[node] = pontos[node].retorna_coordenadas()

    # Após gerar as demandas será printado o grafo com novos dados
    # Cores que serão utilizadas nos nós
    cores = []
    # Tamanho dos nós que serão plotados no grafo
    tamanhos = []

    # Percorre os nós para adicionar informações nas duas listas acima
    for node in grafo_cidade_simplificado:

        # Se o nó for o depósito, recebe uma coloração e tamanho único
        if node == DEPOSITO:

            cores.append('blue')
            tamanhos.append(20)
        # Senão, as cores e tamanhos serão definidos a partir da quantidade de lixo que aquele ponto possui
        else:

            qtd_lixo = pontos_otimizados.get(node).quantidade_lixo

            # A quantidade total de lixo da cidade é incrementada
            quantidade_lixo_cidade += qtd_lixo

            if qtd_lixo <= 10:

                cores.append('green')
                tamanhos.append(2)
            elif 10 < qtd_lixo <= 20:

                cores.append('yellow')
                tamanhos.append(5)
            else:

                cores.append('red')
                tamanhos.append(10)

    # Desenha a figura e salva com o nome, cores e tamanho definidos
    nx.draw(grafo_cidade_simplificado, node_size=tamanhos, node_color=cores, alpha=0.5, with_labels=False,
            pos=coordenadas_pontos)
    plt.savefig(nome_arquivo, dpi=500)

    # Limpa a figura para evitar que o marplotlib se "lembre" da figura
    plt.clf()

    # Fecha a instância do pyplot para que nenhum lixo de memória seja inserido na próxima imagem
    plt.close()

    # Realiza a coleta de lixo de memória
    gc.collect()


# Função que realiza o agrupamento de pontos próximos
def k_means(n_cluster):

    # Monta a matriz com as coordenadas
    matriz = []

    # Passa por todos os pontos otimizados
    for ponto in pontos_otimizados.values():

        # Garante que o depósito não será levado em conta no agrupamento
        if ponto.id == DEPOSITO:
            continue

        # Insere as coordenadas na matriz
        matriz.append([float(ponto.latitude), float(ponto.longitude)])

        # E reseta os agrupamentos dos pontos
        ponto.id_agrupamento = -1

    # Cria o array pela biblioteca do numpy
    coordenadas_pontos = np.array(matriz)

    # Realiza uma instância do algoritmo do kmeans
    kmeans = KMeans(n_cluster, init='k-means++', n_init=10, max_iter=100)

    # Executa o kmeans para encontrar a localização que devem ficar os agrupamentos
    pred_y = kmeans.fit_predict(coordenadas_pontos)

    # Dicionário que agrupa os pontos com base nos seus respectivos agrupamentos
    pontos_agrupados = {}

    # Associa o dicionário de pontos aos seus respectivos agrupamentos
    cont = 0

    # Nesse loop cada ponto será identificado com seu respectivo agrupamento
    # E também serão organizados os pontos com o mesmo agrupamento
    for ponto in pontos_otimizados.values():

        # Pula o depósito pois ele foi ignorado ao fazer os agrupamentos
        if ponto.id == DEPOSITO:
            continue

        # Verifica antes se o ponto já não está associado a um agrupamento
        if ponto.id_agrupamento == -1:

            ponto.id_agrupamento = pred_y[cont]

            # Se o dicionário que agrupa os pontos ainda não tiver aquela chave
            # Significa que nenhum ponto daquele cluster foi inserido ainda
            if ponto.id_agrupamento not in pontos_agrupados.keys():

                # Insere a chave do cluster e o seu respectivo ponto
                pontos_agrupados[ponto.id_agrupamento] = [ponto]
            else:

                # Senão o agrupamento já existe no dicionário
                # Então o ponto é simplesmente inserido
                pontos_agrupados[ponto.id_agrupamento].append(ponto)

        # Incrementa o contador
        cont += 1

    # Gera uma imagem dos agrupamentos gerados pelo k-means
    # Utilizada somente para testes
    """plt.scatter(coordenadas_pontos[:, 1], coordenadas_pontos[:, 0], c=pred_y)

    plt.grid()

    plt.scatter(kmeans.cluster_centers_[:, 1], kmeans.cluster_centers_[:, 0], s=70, c='red', )

    plt.show()"""

    # Retorna os pontos divididos pelos agrupamentos
    return pontos_agrupados


# Função que realiza o processamento das rotas nos agrupamentos gerados
def processamento_rotas(geracoes, populacao, mutacao, crossover):

    # O tamanho da população deve ser sempre par
    nsga = NSGA2(geracoes, populacao, mutacao, crossover, MAX_CAMINHOES, 2, MAX_CLUSTERS)

    return nsga.run()


# Função que calcula a distância entre dois pontos, utilizando a função pronta da biblioteca geopy
def calcula_distancia_pontos(lat_ponto1, lon_ponto1, lat_ponto2, lon_ponto2):
    # Converte as coordenadas em tuplas
    coord_pnt1 = (lat_ponto1, lon_ponto1)
    coord_pnt2 = (lat_ponto2, lon_ponto2)

    return geopy.distance.geodesic(coord_pnt1, coord_pnt2).m


def retorna_maior_label():
    return Ponto.novo_label


# Converte o grafo otimizado para um grafo euleriano
# Para que um grafo seja euleriano, todos os vértices dele devem possuir grau par
def converte_grafo_euleriano(grafo):
    # Conecta o grafo para que seja possível realizar o circuito
    if not nx.is_connected(grafo):
        conecta_grafo(grafo)

    # Utiliza a função pronta do networkx que converte o grafo para um grafo euleriano
    return nx.eulerize(grafo)


# Se o subgrafo do cluster for desconexo, ele deve ter seus pontos conectados
def conecta_grafo(grafo):
    # Variável que armazena os pontos da primeira componente conexa, que é a maior
    primeiro_componente = None

    # Para cada componente conexa do grafo
    for componentes in nx.connected_components(grafo):

        # Se não for a primeira são feitas operações para conectar todas as componentes a primeira
        if primeiro_componente is not None:

            # Converte o set para uma lista
            comp = list(componentes)

            # Lista os pontos pela sua proximidade com o ponto atual
            proximos = nx.single_source_shortest_path_length(grafo_cidade_simplificado, comp[0])

            # Para cada ponto listado acima
            for node_prox in proximos:

                # Verifica se o ponto está na primeira componente e se não é o mesmo ponto
                # Assim é gerantido que o ponto será ligado ao mais próximo presente na primeira componente conexa
                if (node_prox in primeiro_componente) and (comp[0] != node_prox):
                    distancia_pontos = nx.single_source_dijkstra(grafo_cidade_simplificado, comp[0], node_prox)
                    grafo.add_edge(comp[0], node_prox, weight=distancia_pontos[0])

                    break
        else:

            # Obtém os pontos da componente conexa maior
            primeiro_componente = componentes


def get_configuration_for_execute():
    with open("configurations.log", "r") as input_file:

        for line in input_file:

            if not line.startswith("#"):
                return eval(line)

    return False


def save_configuration_executed(config):
    line_to_modify = f'{config}\n'

    with open("configurations.log", "r") as input_file, tempfile.NamedTemporaryFile("w", delete=False) as output_file:

        for line in input_file:

            if line == line_to_modify:

                output_file.write("# " + line)
            else:

                output_file.write(line)

    shutil.move(output_file.name, "configurations.log")


def projeto_fatorial():

    global cache_mapas_eulerizados

    # Monta o 'cache' dos mapas eulerizados
    monta_cache_mapas()
    # Fixados
    # a1, a2 = 300, 400  # Gerações
    ger = 500

    # b1, b2 = 100, 150  # Tamanho da população
    pop = 100

    # c1, c2 = 0.45, 0.5  # Taxa de mutação
    mut = 0.4

    # d1, d2 = 0.65, 0.7  # Taxa de crossover
    cro = 0.6

    configurations = {"1": [ger, pop, mut, cro]}
    """configurations = {
        "1": [a2, b2, c2, d2],
        "2": [a2, b2, c2, d1],
        "3": [a2, b2, c1, d2],
        "4": [a2, b2, c1, d1],
        "5": [a2, b1, c2, d2],
        "6": [a2, b1, c2, d1],
        "7": [a2, b1, c1, d2],
        "8": [a2, b1, c1, d1],
        "9": [a1, b2, c2, d2],
        "10": [a1, b2, c2, d1],
        "11": [a1, b2, c1, d2],
        "12": [a1, b2, c1, d1],
        "13": [a1, b1, c2, d2],
        "14": [a1, b1, c2, d1],
        "15": [a1, b1, c1, d2],
        "16": [a1, b1, c1, d1]
    }"""

    # Lista com as linhas do arquivo
    linhas = []

    # Cria o arquivo de configurações
    with open("configurations.log", "w") as arq_configuracao:

        # Passa por cada uma das configurações
        for config in configurations.keys():

            # Número de vezes que cada configuração será testada
            for iteracao in range(3):
                # Adiciona a linha na lista
                linhas.append(f"[{config}, {iteracao}]\n")

        # Após todas as linhas geradas, percorre a lista que as armazena
        while linhas:
            # Escrevendo no arquivo uma linha aleatoria, para que uma configuração não seja prejudicada tendo testes
            # executados um após o outro
            linha = random.choice(linhas)
            arq_configuracao.write(linha)
            linhas.remove(linha)

    arq_configuracao.close()

    configuration_and_iteration = get_configuration_for_execute()

    # Executa as configurações do arquivo gerado acima
    while configuration_and_iteration:

        print(f"Iteração {str(configuration_and_iteration[1])}: Configuração {str(configuration_and_iteration[0])}\n")

        parameter = configurations[str(configuration_and_iteration[0])]
        processamento_rotas(parameter[0], parameter[1], parameter[2], parameter[3])

        save_configuration_executed(configuration_and_iteration)
        configuration_and_iteration = get_configuration_for_execute()


# Calcula as medianas dos arquivos de saída gerados
def calcula_medianas():
    # Itera sobre os arquivos de saida
    for filename in os.listdir("saida/Resultados"):

        # Lista que armazena os valores de hypervolume
        hypervolumes = []

        # Lista que aramzena os valores de tempo de execução
        tempos = []

        # Abre o arquivo para ser lido e atualizado
        # with open(filename, "a+") as arquivo:
        with open("saida/Resultados/" + filename, "r") as input_file, tempfile.NamedTemporaryFile("w",
                                                                                                  delete=False) as output_file:

            # Itera sobre as linhas do arquivo
            for linha in input_file:
                # O que tiver antes da vírgula é o valor de hypervolume
                hypervolumes.append(float(linha.split(',')[0]))

                # E o que tiver depois é o valor do tempo de execução
                tempos.append(float(linha.split(',')[1]))

                # Escreve a linha novamente no arquivo
                output_file.write(linha)

            # Ordena as listas
            hypervolumes.sort()
            tempos.sort()

            # Cálculo da mediana
            # Identifica se a lista é de tamanho ímpar ou par
            if len(hypervolumes) % 2 == 0 and len(tempos) % 2 == 0:

                # Se for par calcula a média entre os dois elementos centrais
                media_hypervolume = (hypervolumes[ceil(len(hypervolumes) / 2) - 1] +
                                     hypervolumes[ceil(len(hypervolumes) / 2)]) / 2
                media_tempos = (tempos[ceil(len(tempos) / 2) - 1] + tempos[ceil(len(tempos) / 2)]) / 2

                output_file.write(f"\n\n{media_hypervolume},{media_tempos}")
            else:

                # Se for ímpar calcula o meio da lista
                output_file.write(f"\n\n{hypervolumes[ceil(len(hypervolumes) / 2) - 1]},"
                                  f"{tempos[ceil(len(hypervolumes) / 2) - 1]}")

        shutil.move(output_file.name, "saida/Resultados/" + filename)


# Monta o 'cache'
def monta_cache_mapas():

    global cache_mapas_eulerizados

    print("Gerando 'cache' dos mapas...")

    # Vai do mínimo ao máximo de clusters
    # O mínimo foi definido como 2 para abranger o mínimo possível em qualquer execução
    for n_cluster in range(2, MAX_CLUSTERS + 1):

        # Realiza a clusterização com o número de clusters atual
        pontos_clusterizados = k_means(n_cluster)

        # Inicia a lista de subgrafos eulerizados
        subgrafos_eularizados = {}

        # Percorre os agrupamentos realizados pelo k-means
        for id_cluster, cluster in pontos_clusterizados.items():

            # Monta um subgrafo com o agrupamento
            grafo_cluster = grafo_cidade_simplificado.subgraph(ponto.id for ponto in cluster).copy()

            # Verifica se o subgrafo é euleriano
            if not nx.is_eulerian(grafo_cluster):

                # Transforma em um grafo euleriano
                grafo_cluster = converte_grafo_euleriano(grafo_cluster)

            # Adiciona nos subgrafos eulerizados
            subgrafos_eularizados[id_cluster] = grafo_cluster

        print(f"Cache do mapeamento para {n_cluster} clusters gerado")

        # Insere na lista global para ser acessada posteriormente
        cache_mapas_eulerizados[n_cluster] = [pontos_clusterizados, subgrafos_eularizados]


# Captura a altitude dos pontos
def captura_altitude():

    payload = {}
    headers = {}

    # identifica de qual mapa serão obtidas as altitudes
    if MAPA == 'F':

        arquivo = open('entrada/alturas.osm', 'a')
    else:

        arquivo = open('entrada/alturas_lagoa.osm', 'a')

    # Itera sobre os pontos do mapa
    for id_ponto, ponto in pontos.items():

        # É necessário ter um tempo entre as requisições para não ser desconectado
        time.sleep(2)

        # URL da requisição
        url = f"https://api.opentopodata.org/v1/test-dataset?locations={ponto.latitude},{ponto.longitude}"

        # Obtém a resposta da API
        response = requests.request("GET", url, headers=headers, data=payload)

        # Se for uma resposta de sucesso, escreve os dados no arquivo
        if response.status_code == 200:

            texto_resposta = response.text.split()

            arquivo.write(f"id = \"{id_ponto}\" altitude = \"{texto_resposta[7][:-1]}\"\n")
        else:

            print(response.reason)
            arquivo.close()
            break

    arquivo.close()
