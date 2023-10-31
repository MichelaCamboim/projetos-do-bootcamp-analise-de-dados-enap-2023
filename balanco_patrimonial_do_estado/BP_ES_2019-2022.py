import numpy as np
import os, pandas as pd, re
from datetime import date
import requests
import streamlit as st
import warnings
warnings.filterwarnings('ignore')
import seaborn as sns
import plotly.express as px
import plotly.io as pio
from sklearn import preprocessing

st.set_page_config(page_title="Balanço Patrimonial do Estado do Espírito Santo 🏢", page_icon= '🏢', layout="wide")

def build_path(subfolder = 'data'):
    folderpath = os.path.join(os.getcwd(), 
                              'projeto', subfolder)
    folderpath = os.path.abspath(folderpath)
    if not os.path.exists(folderpath): 
        os.makedirs(folderpath)
    return folderpath

@st.cache_data
def get_dados_pcasp(
        filename='CPU_PCASP_2022.xlsx'):
    filepath = os.path.join(build_path(), filename)
    return pd.read_excel(filepath, sheet_name= 'Federação 2022')


pcasp = get_dados_pcasp()

pcasp = pcasp.drop(columns=['FUNÇÃO','STATUS','NATUREZA DO SALDO','CONTROLE','ÍTEM','SUBÍTEM'])

pcasp = pcasp.loc[pcasp['CLASSE'].isin([1, 2])]

pcasp.loc[pcasp['TÍTULO.1'] == 'OBRIGAÇÕES TRABALHISTAS, PREVIDENCIÁRIAS E ASSISTENCIAIS A PAGAR A LONGO PRAZO','TÍTULO.1'] = 'OBRIGAÇÕES TRAB. A LONGO PRAZO'

pcasp.loc[pcasp['TÍTULO.1'] == 'OBRIGAÇÕES TRABALHISTAS, PREVIDENCIÁRIAS E ASSISTENCIAIS A PAGAR A CURTO PRAZO','TÍTULO.1'] = 'OBRIGAÇÕES TRAB. A CURTO PRAZO'

pcasp['NÍVEL3'] = pcasp['CLASSE'].astype(str) + pcasp['GRUPO'].astype(str) + pcasp['SUBGRUPO'].astype(str)

pcasp['NÍVEL2'] = pcasp['CLASSE'].astype(str) + pcasp['GRUPO'].astype(str)

pcasp['NÍVEL1'] = pcasp['CLASSE'].astype(str)

pcasp_nivel_3 = pcasp.loc[(pcasp['SUBGRUPO']!= 0) & (pcasp['TÍTULO']== 0)]

pcasp_nivel_2 = pcasp.loc[(pcasp['GRUPO']!= 0) & (pcasp['SUBGRUPO']== 0)]

pcasp_nivel_1 = pcasp.loc[(pcasp['GRUPO']== 0)]

pcasp_nivel_1_2_3 = pd.concat([pcasp_nivel_1,pcasp_nivel_2,pcasp_nivel_3],axis=0)


build_path()

@st.cache_data
def get_dados_instancia(filename='instancia_MSC_API.csv'):
    filepath = os.path.join(build_path(), filename)
    return pd.read_csv(filepath, sep=';')

instancia = get_dados_instancia()

instancia = instancia.drop(columns=['tipo_matriz','cod_ibge','poder_orgao','financeiro_permanente','ano_fonte_recursos','fonte_recursos','mes_referencia','divida_consolidada','data_referencia','entrada_msc','tipo_valor','complemento_fonte'])

instancia = instancia.rename(columns={'classe_conta':'NÍVEL1', 'conta_contabil':'CONTA', 'exercicio': 'EXERCÍCIO', 'valor':'VALOR', 'natureza_conta':'NATUREZA_VALOR'})

instancia['CONTA'] = instancia['CONTA'].astype(str)

#  Multiplica por 1 - Desnecessária
instancia.loc[instancia['NÍVEL1'].isin([1]) & 
              (instancia['NATUREZA_VALOR']=='D'), 'VALOR'] = instancia['VALOR']*1

#  Multiplica por -1
instancia.loc[instancia['NÍVEL1'].isin([1]) & 
              (instancia['NATUREZA_VALOR']=='C'), 'VALOR'] = instancia['VALOR']*(-1)

#  Multiplica por 1 - Desnecessária
instancia.loc[instancia['NÍVEL1'].isin([2]) & 
              (instancia['NATUREZA_VALOR']=='C'), 'VALOR'] = instancia['VALOR']*1

#  Multiplica por -1
instancia.loc[instancia['NÍVEL1'].isin([2]) & 
              (instancia['NATUREZA_VALOR']=='D'), 'VALOR'] = instancia['VALOR']*(-1)

instancia['NÍVEL3'] = instancia['CONTA'].str.slice(0, 3)
instancia['NÍVEL2'] = instancia['CONTA'].str.slice(0,2)

coluna = [col for col in instancia if col != 'NÍVEL1'] + ['NÍVEL1']

instancia=instancia[coluna]

instancia_grouped = instancia[['VALOR']].groupby([instancia['EXERCÍCIO'], instancia['NÍVEL3'], instancia['NATUREZA_VALOR']])

instancia_soma_nivel_3 = instancia[['VALOR']].groupby([instancia['EXERCÍCIO'], instancia['NÍVEL3']]).sum()

instancia_soma_nivel_2 = instancia[['VALOR']].groupby([instancia['EXERCÍCIO'], instancia['NÍVEL2']]).sum()

instancia_soma_nivel_1 = instancia[['VALOR']].groupby([instancia['EXERCÍCIO'], instancia['NÍVEL1']]).sum()

instancia_soma_nivel_3=instancia_soma_nivel_3.reset_index(level=['NÍVEL3','EXERCÍCIO'])

instancia_soma_nivel_2 = instancia_soma_nivel_2.reset_index(level=['NÍVEL2','EXERCÍCIO'])

instancia_soma_nivel_1 = instancia_soma_nivel_1.reset_index(level=['NÍVEL1','EXERCÍCIO'])

balanco_nivel_3 = pd.merge(pcasp_nivel_3, instancia_soma_nivel_3, how='inner')

balanco_nivel_3 = balanco_nivel_3.sort_values(by=['EXERCÍCIO','CONTA'])

balanco_nivel_3 = balanco_nivel_3.drop(columns=['CLASSE','GRUPO','SUBGRUPO','TÍTULO','SUBTÍTULO'])

balanco_nivel_2 = pd.merge(pcasp_nivel_2, instancia_soma_nivel_2, how='inner')

balanco_nivel_2 = balanco_nivel_2.sort_values(by=['EXERCÍCIO','CONTA'])

balanco_nivel_2 = balanco_nivel_2.drop(columns=['CLASSE','GRUPO','SUBGRUPO','TÍTULO','SUBTÍTULO'])

instancia_soma_nivel_1['NÍVEL1'] = instancia_soma_nivel_1['NÍVEL1'].astype(str)

balanco_nivel_1 = pd.merge(pcasp_nivel_1, instancia_soma_nivel_1, how='inner')

balanco_nivel_1 = balanco_nivel_1.sort_values(by=['EXERCÍCIO','CONTA'])

balanco_nivel_1 = balanco_nivel_1.drop(columns=['CLASSE','GRUPO','SUBGRUPO','TÍTULO','SUBTÍTULO'])

balanco_123 = pd.concat([balanco_nivel_1,balanco_nivel_2,balanco_nivel_3],axis=0)

balanco_123 = balanco_123.sort_values(by=['EXERCÍCIO','CONTA'])

balanco_123 = balanco_123.drop(columns=['NÍVEL3','NÍVEL2','NÍVEL1'])
lista_exercicios = list(set(balanco_123['EXERCÍCIO']))
balanco = []
for ano in lista_exercicios:
    balanco_ano = balanco_123.loc[balanco_123['EXERCÍCIO'] == ano]
    balanco_ano = balanco_ano.rename(columns={'VALOR': f'{ano}'})
    balanco_ano = balanco_ano.drop(columns=['EXERCÍCIO'])
    balanco.append(balanco_ano)
balanco_final = pd.merge(balanco[0], balanco[1], how='outer', on=['CONTA','TÍTULO.1'])
balanco_final = pd.merge(balanco_final, balanco[2], how='outer', on=['CONTA','TÍTULO.1'])
balanco_final = pd.merge(balanco_final, balanco[3], how='outer', on=['CONTA','TÍTULO.1'])
balanco_final = balanco_final.sort_values(by='CONTA')

#pd.options.display.float_format = 'R${:,.2f}'.format

balanco_final_exercicio = balanco_final.T
lista = []
for i in range(len(balanco_final)):
    lista.append( list(balanco_final_exercicio.loc['TÍTULO.1'])[i])

balanco_final_exercicio = balanco_final_exercicio.rename(columns=balanco_final_exercicio.iloc[1])
balanco_final_exercicio = balanco_final_exercicio[2:]
balanco_final_exercicio.index.names = ['EXERCÍCIO']
balanco_final_exercicio = balanco_final_exercicio.reset_index(level=['EXERCÍCIO'])
balanco_final['CONTA'] = balanco_final['CONTA'].astype(str)
balanco_final['CLASSE'] = balanco_final['CONTA'].str.slice(0,1)
balanco_final = balanco_final.rename(columns={2019: '2019', 2020: '2020', 2021: '2021', 2022: '2022'})




st.markdown('# Balanço Patrimonial do Estado do Espírito Santo 🏢')
st.markdown("#### Série Histórica 2019-2022 a partir da MSC ")
st.markdown("---")

with st.sidebar:
    #escolha_ente = st.sidebar.selectbox('Escolha o Ente:', ('ES', ''))
    st.sidebar.markdown('# Balanço Patrimonial do Estado do Espírito Santo 🏢')
    st.sidebar.markdown("---")
    st.sidebar.markdown("##### Projeto desenvolvido no Curso Bootcamp Análise de Dados 2023, promovido pela ENAP.")
    st.sidebar.markdown("Equipe: Ana Paula Giancoli, Eugênia Giancoli, Gislaine Messias e Mariana Hermínia")
    st.sidebar.markdown("---")
    st.markdown("#### Série Histórica 2019-2022 a partir da MSC:")
    st.sidebar.markdown("##### Escolha um ou mais anos: ")
    ano2019=st.sidebar.checkbox("2019", value=True)
    ano2020=st.sidebar.checkbox("2020")
    ano2021=st.sidebar.checkbox("2021")
    ano2022=st.sidebar.checkbox("2022")
    listaAnos=[]
    if ano2019:
        listaAnos.append("2019")
    if ano2020:
        listaAnos.append("2020")
    if ano2021:
        listaAnos.append("2021")
    if ano2022:
        listaAnos.append("2022")

    st.sidebar.markdown("---")
    st.markdown(f'#### Série Histórica 2019-2022 selecionada pela Conta: ')
    escolha_descr = st.sidebar.selectbox('Escolha uma das contas: ', balanco_final['TÍTULO.1'])

    
# Gráfico Geral com Série histórica por contas
# chart_data = pd.DataFrame(balanco_final, columns=listaAnos)
# st.bar_chart(chart_data)
# st.markdown("---")

st.bar_chart(balanco_final, y=listaAnos, x='CONTA', color=listaAnos[0])
st.markdown("---")  

st.markdown("#### Série Histórica 2019-2022 selecionada pela Conta ")
col3, col4 = st.columns([3, 5])
with col3:
    pass

with col4:
    st.markdown(f"##### {escolha_descr} ")
    balanco = pd.DataFrame(balanco_final_exercicio, columns=['EXERCÍCIO', escolha_descr])

st.bar_chart(balanco_final_exercicio, y=escolha_descr,x='EXERCÍCIO',color=escolha_descr)
st.markdown("---")    

# Criar colunas em balanco_final para organizar o treemap nas suas subcontas
balanco_final_map = balanco_final.copy()
# Cria coluna que indica se a conta é Ativo ou Passivo e PL
balanco_final_map['N1']=' '
#Ativo
balanco_final_map.loc[balanco_final_map['CONTA'].str.slice(0,1)== '1', 'N1'] = 'ATIVO'
#Passivo e PL
balanco_final_map.loc[balanco_final_map['CONTA'].str.slice(0,1) == '2', 'N1'] ='PASSIVO E PATRIMÔNIO LIQUIDO'
#Para conta que são as próprias N1, deixe o campo vazio
#balanco_final.loc[balanco_final['CONTA'].str.slice(1,2) == '0', 'N1'] =' '
#Para conta que são subcontas de N1 e N2, deixe o campo vazio
#balanco_final.loc[balanco_final['CONTA'].str.slice(2,3) != '0', 'N1'] =' '

# Cria coluna que indica de a conta é Ativo(Ativo Circulante ou Ativo Não Circulante)
# ou Passivo e PL(Passivo Circulante ou Passivo Não Circulante ou PL)
balanco_final_map['N2']=' '
#Ativo Circulante
balanco_final_map.loc[balanco_final_map['CONTA'].str.slice(0,2) == '11', 'N2'] = 'ATIVO CIRCULANTE'
#Ativo Não Circulante
balanco_final_map.loc[balanco_final_map['CONTA'].str.slice(0,2) == '12', 'N2'] = 'ATIVO NÃO CIRCULANTE'
#Passivo Circulante
balanco_final_map.loc[balanco_final_map['CONTA'].str.slice(0,2) == '21', 'N2'] ='PASSIVO CIRCULANTE'
#Passivo Não Circulante
balanco_final_map.loc[balanco_final_map['CONTA'].str.slice(0,2) == '22', 'N2'] ='PASSIVO NAO-CIRCULANTE'
#PL
balanco_final_map.loc[balanco_final_map['CONTA'].str.slice(0,2) == '23', 'N2'] ='PATRIMÔNIO LIQUIDO'
#Para conta que são as próprias N1 e N2, deixe o campo vazio
#balanco_final.loc[balanco_final['CONTA'].str.slice(2,3) == '0', 'N2'] =' '

# Elimina as contas cumulativas
balanco_final_map = balanco_final_map[ (balanco_final_map['TÍTULO.1'] != 'ATIVO') & (balanco_final_map['TÍTULO.1'] != 'PASSIVO E PATRIMÔNIO LIQUIDO') & (balanco_final_map['TÍTULO.1'] != 'ATIVO CIRCULANTE') & (balanco_final_map['TÍTULO.1'] != 'ATIVO NÃO CIRCULANTE') & (balanco_final_map['TÍTULO.1'] != 'PASSIVO CIRCULANTE') & (balanco_final_map['TÍTULO.1'] != 'PASSIVO NAO-CIRCULANTE') & (balanco_final_map['TÍTULO.1'] != 'PATRIMÔNIO LIQUIDO')]

balanco_normalizado = balanco_final_map.copy()


for ano in listaAnos:
    # Gráfico Treemap ATIVO                             
    ativo = px.treemap(balanco_final_map.loc[balanco_final_map['CLASSE'] == '1'], 
                     path = ['N1','N2', 'TÍTULO.1'], 
                     values = listaAnos[listaAnos.index(ano)], 
                     color_continuous_scale='RdBu',
                     color = listaAnos[listaAnos.index(ano)],             
                     color_continuous_midpoint=0)

    ativo.update_layout(margin = dict(t=50, l=25, r=25, b=25))   
    coluna_ano = listaAnos[listaAnos.index(ano)]
    
    if balanco_final_map[coluna_ano].min() < 0 :        
        listanorm = preprocessing.normalize([balanco_normalizado[coluna_ano].values.tolist()]) 
        coluna_ano = coluna_ano+'ABS'
        listanormal = listanorm-(listanorm.min()*2)
        balanco_normalizado[coluna_ano] = pd.DataFrame(listanormal).T
    
    # Gráfico Treemap PASSIVO
    passivo = px.treemap(balanco_normalizado.loc[balanco_normalizado['CLASSE'] == '2'], 
                     path = ['N1','N2', 'TÍTULO.1'], 
                     values = coluna_ano, 
                     color_continuous_scale='RdBu',
                     color = listaAnos[listaAnos.index(ano)],             
                     color_continuous_midpoint=np.average(balanco_normalizado[coluna_ano]))

    passivo.update_layout(margin = dict(t=50, l=25, r=25, b=25))
    #st.markdown("---")
    
    # Atualizar legenda dos TreeMaps
    ativo.update_layout(title_text='Mapa do Ativo de ' + listaAnos[listaAnos.index(ano)], title_font=dict(size=24), title_x = 0.025)
    passivo.update_layout(title_text='Mapa do Passivo e Patrimônio Líquido de ' + listaAnos[listaAnos.index(ano)], title_font=dict(size=24), title_x = 0.025)
    
    # Layout com duas colunas
    col1, col2 = st.columns(2)

    # Colocar TreeMaps nas colunas
    with col1:
        st.plotly_chart(ativo, use_container_width=True)

    with col2:
        st.plotly_chart(passivo, use_container_width=True)
