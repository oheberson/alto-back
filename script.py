from pypdf import PdfReader
import re
import json
from datetime import datetime, date
import pytz
import os

def get_home_and_away_stats(splitter, string):

    home_stat = string.split(splitter)[1].strip()
    away_stat = string.split(splitter)[2].strip()

    return home_stat, away_stat

def remove_accents(input_str):
        # Translation table for common accented characters
        accents = str.maketrans(
            "çãàáâäéèêëíìîïóòôõöúùûüñÁÀÂÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÑ",
            "caaaaaeeeeiiiiooooouuuunAAAAAEEEEIIIIOOOOUUUUN"
        )
        return input_str.translate(accents)

def find_pdf_by_date(date_str):
    pdf_folder = os.path.join(os.getcwd(), "pdfs")
    
    if not os.path.isdir(pdf_folder):
        print(f"The folder 'pdfs' does not exist in the current directory.")
        return None
    
    for filename in os.listdir(pdf_folder):
        if filename.endswith(".pdf") and date_str in filename:
            print(f"Found PDF file: {filename}")
            return filename
    
    return None

sao_paulo_tz = pytz.timezone("America/Sao_Paulo")
today_date = date.today()
today_date = datetime.combine(today_date, datetime.min.time())
today_date = sao_paulo_tz.localize(today_date)

pdf_string_date_to_look_for = f"{today_date.day:02d}-{today_date.month:02d}"
file_name = find_pdf_by_date(pdf_string_date_to_look_for)

if not file_name:
    raise Exception(f"No PDF file for '{pdf_string_date_to_look_for}' date was found in the 'pdfs' folder.")

print('**** STARTING *****')

pdf = PdfReader(f'pdfs/{file_name}')
len_pages_pdf = len(pdf.pages)

all_matches = []

for i in range(1, len_pages_pdf):
    game_page = pdf.pages[i]
    game_linhas = game_page.extract_text().split('\n')
    game_linhas_len = len(game_linhas)

    match_info = {}

    # Tournament Info
    tournament_infos = game_linhas[0].split()
    match_date = tournament_infos[0]
    time = tournament_infos[1]
    country = tournament_infos[2]
    tournament_name = tournament_infos[3:-2]
    round_number = tournament_infos[-1]
    match_info['tournament_name'] = ' '.join(tournament_name)
    match_info['date'] = match_date
    match_info['time'] = time
    match_info['country'] = country
    match_info['round_number'] = round_number

    # Teams in game
    teams_participating = '-'.join([i.lower() for i in game_linhas[1].split()])
    match_info['teams'] = teams_participating

    # Teams streak
    streaks = game_linhas[2].split()
    if streaks[0] == '-' and streaks[1] == '-':
        continue
    try:
        home_streak = streaks[0]
        away_streak = streaks[9]

        if len(home_streak) < 8 and len(away_streak) <= 8:
            raise IndexError
        if len(home_streak) > 8:
            home_streak = home_streak[:8]
        if len(away_streak) > 8:
            away_streak = away_streak[:8]

    except IndexError:
        # skip not enough streak info
        continue

    match_info['home_streak'] = home_streak
    match_info['away_streak'] = away_streak

    # Common infos
    lines_to_get = [
        'posição na tabela',
        'pontos por jogo',
        'total de jogos',
        'vitórias',
        'porcentagem de vitória',
        'primeiro a marcar na partida',
        'jogos sem sofrer gols',
        'ambas marcam',
        'média de finalizações',
        'média fin no alvo',
        'finalizações para marcar um gol',
        'finalizações no alvo para marcar um gol',
        'xg médio a favor por jogo',
        'xg médio contra por jogo',
        'venceu o primeiro tempo',
        'empatou o primeiro tempo',
        'perdeu o primeiro tempo',
        'venceu o segundo tempo',
        'empatou o segundo tempo',
        'perdeu o segundo tempo',
        'gols de escanteio',
        'terminou a partida com mais escanteios',
        'terminou o 1º tempo com mais escanteios',
        'terminou o 2º tempo com mais escanteios',
        'média de cartões recebidos no 1º tempo',
        'média de cartões recebidos no 2º tempo',
        'mais de 0.5 cards recebidos',
        'mais de 1.5 cards recebidos',
        'mais de 2.5 cards recebidos',
        'mais de 3.5 cards recebidos',
        'mais de 4.5 cards recebidos',
        'mais de 5.5 cards recebidos',
        'mais de 6.5 cards recebidos',
        'mais de 0.5 cartões',
        'mais de 1.5 cartões',
        'mais de 2.5 cartões',
        'mais de 3.5 cartões',
        'mais de 4.5 cartões',
        'mais de 5.5 cartões',
        'mais de 6.5 cartões',
        'mais de 7.5 cartões',
        'mais de 8.5 cartões',
    ]

    titles = [
        'Gols em Casa Gols Fora de Casa'
    ]
    remaining = game_linhas.copy()

    for li in game_linhas:
        li_cp = li.replace('% de Vitórias', 'porcentagem de vitória')
        li_cp = li.replace('Média de Finalizações no alvo', "Média Fin no Alvo")
        li_cp = li.replace('5 cartões recebidos', '5 cards recebidos')
        if li_cp not in titles:
            for item in lines_to_get:
                if item in li_cp.lower():
                    home_stat, away_stat = get_home_and_away_stats(item, li_cp.lower())
                    match_info[f"{'_'.join(remove_accents(item).split())}_home"] = home_stat.replace(',', '.')
                    match_info[f"{'_'.join(remove_accents(item).split())}_away"] = away_stat.replace(',', '.')
                    
                    remaining.remove(li)
                    break
    
    for i in remaining:
        if len(i) == 1:
            remaining.remove(i)

    for i, l in enumerate(remaining):
        if i == 4:
            home_position_as_mando = l.split('Posição como Mandante')[1].split('Posição')[0].strip()
            away_position_as_mando = l.split('Posição como Visitante')[-1].strip()

            match_info['posicao_como_mandante'] = home_position_as_mando.replace(',', '.')
            match_info['posicao_como_visitante'] = away_position_as_mando.replace(',', '.')
        
        if i == 5:
            home_fail_to_score_as_mando, away_fail_to_score_as_mando = get_home_and_away_stats('falhou em marcar', l.lower())

            match_info['falhou_em_marcar_como_mandante'] = home_fail_to_score_as_mando
            match_info['falhou_em_marcar_como_visitante'] = away_fail_to_score_as_mando
        
        if i == 11:
            home_avg_goals_as_mando = l.split('Média total de gols em casa')[1].split('Média')[0].strip()
            away_avg_goals_as_mando = l.split('Média total de gols fora de casa')[-1].strip()

            match_info['media_gols_como_mandante'] = home_avg_goals_as_mando.replace(',', '.')
            match_info['media_gols_como_visitante'] = away_avg_goals_as_mando.replace(',', '.')
        
        if i == 85:
            home_avg_cards_received_as_mando = l.split('Média de cartões recebidos em casa')[1].split('Média')[0].strip()
            away_avg_cards_received_as_mando = l.split('Média de cartões recebidos fora')[-1].strip()

            match_info['media_cartoes_como_mandante'] = home_avg_cards_received_as_mando.replace(',', '.')
            match_info['media_cartoes_como_visitante'] = away_avg_cards_received_as_mando.replace(',', '.')
        
        if i == 86:
            home_total_avg_cards_as_mando = l.split('Média Total de cartões nos jogos em casa')[1].split('Média')[0].strip()
            away_total_avg_cards_as_mando = l.split('Média Total de cartões nos jogos fora')[-1].strip()

            match_info['media_total_cartoes_como_mandante'] = home_total_avg_cards_as_mando.replace(',', '.')
            match_info['media_total_cartoes_como_visitante'] = away_total_avg_cards_as_mando.replace(',', '.')

    ## From 7 to 10: Gols em casa/fora
    cell_titles = [
        'gols marcados',
        'gols sofridos',
        'média de gols scored',
        'média de gols against'
    ]
    for i, l in enumerate(remaining[6:10]):
        l = l.replace('Média de gols marcados', 'média de gols scored')
        l = l.replace('Média de gols sofridos', 'média de gols against')
        for item in cell_titles:
            if item in l.lower():
                home_stat, away_stat = get_home_and_away_stats(item, l.lower())
                match_info[f"{'_'.join(remove_accents(item).split())}_como_mandante"] = home_stat.replace(',', '.')
                match_info[f"{'_'.join(remove_accents(item).split())}_como_visitante"] = away_stat.replace(',', '.')
                break

    ## From 15 to 20: 1T
    cell_titles = [
        'falhou em marcar',
        'não sofreu gols',
        'gols marcados',
        'gols sofridos',
        'média de gols scored',
        'média de gols against'
    ]
    for i, l in enumerate(remaining[15:21]):
        l = l.replace('Média de gols marcados', 'média de gols scored')
        l = l.replace('Média de gols sofridos', 'média de gols against')
        for item in cell_titles:
            if item in l.lower():
                home_stat, away_stat = get_home_and_away_stats(item, l.lower())
                match_info[f"{'_'.join(remove_accents(item).split())}_1T_como_mandante"] = home_stat.replace(',', '.')
                match_info[f"{'_'.join(remove_accents(item).split())}_1T_como_visitante"] = away_stat.replace(',', '.')
                break

    ## From 23 to 29: 2T
    cell_titles = [
        'falhou em marcar',
        'não sofreu gols',
        'gols marcados',
        'gols sofridos',
        'média de gols scored',
        'média de gols against'
    ]
    for i, l in enumerate(remaining[23:29]):
        l = l.replace('Média de gols marcados', 'média de gols scored')
        l = l.replace('Média de gols sofridos', 'média de gols against')
        for item in cell_titles:
            if item in l.lower():
                home_stat, away_stat = get_home_and_away_stats(item, l.lower())
                match_info[f"{'_'.join(remove_accents(item).split())}_2T_como_mandante"] = home_stat.replace(',', '.')
                match_info[f"{'_'.join(remove_accents(item).split())}_2T_como_visitante"] = away_stat.replace(',', '.')
                break

    ## From 31 to 35: types of goals scored
    cell_titles = [
        'gols de cabeça',
        'gols de faltas diretas',
        'gols de fora da área',
        'gols de penaltis',
    ]
    for i, l in enumerate(remaining[31:35]):
        for item in cell_titles:
            if item in l.lower():
                home_stat, away_stat = get_home_and_away_stats(item, l.lower())
                match_info[f"{'_'.join(remove_accents(item).split())}_marcados_como_mandante"] = home_stat.replace(',', '.')
                match_info[f"{'_'.join(remove_accents(item).split())}_marcados_como_visitante"] = away_stat.replace(',', '.')
                break

    ## From 36 to 40: types of goals against
    cell_titles = [
        'gols de cabeça',
        'gols de faltas diretas',
        'gols de fora da área',
        'gols de penaltis',
    ]
    for i, l in enumerate(remaining[36:40]):
        for item in cell_titles:
            if item in l.lower():
                home_stat, away_stat = get_home_and_away_stats(item, l.lower())
                match_info[f"{'_'.join(remove_accents(item).split())}_sofridos_como_mandante"] = home_stat.replace(',', '.')
                match_info[f"{'_'.join(remove_accents(item).split())}_sofridos_como_visitante"] = away_stat.replace(',', '.')
                break

    ## From 42 to 45: total number of goals
    cell_titles = [
        'over 0.5',
        'over 1.5',
        'over 2.5',
    ]
    for i, l in enumerate(remaining[42:45]):
        for item in cell_titles:
            if item in l.lower():
                home_stat, away_stat = get_home_and_away_stats(item, l.lower())
                match_info[f"{'_'.join(remove_accents(item).split())}_gols_totais_como_mandante"] = home_stat.replace(',', '.')
                match_info[f"{'_'.join(remove_accents(item).split())}_gols_totais_como_visitante"] = away_stat.replace(',', '.')
                break

    ## From 46 to 49: total number of goals made
    cell_titles = [
        'over 0.5 gols',
        'over 1.5 gols',
        'over 2.5 gols',
    ]
    for i, l in enumerate(remaining[46:49]):
        for item in cell_titles:
            if item in l.lower():
                home_stat, away_stat = get_home_and_away_stats(item, l.lower())
                match_info[f"{'_'.join(remove_accents(item).split())}_gols_marcados_como_mandante"] = home_stat.replace(',', '.')
                match_info[f"{'_'.join(remove_accents(item).split())}_gols_marcados_como_visitante"] = away_stat.replace(',', '.')
                break

    ## From 50 to 53: total number of goals against
    cell_titles = [
        'over 0.5 gols',
        'over 1.5 gols',
        'over 2.5 gols',
    ]
    for i, l in enumerate(remaining[50:53]):
        for item in cell_titles:
            if item in l.lower():
                home_stat, away_stat = get_home_and_away_stats(item, l.lower())
                match_info[f"{'_'.join(remove_accents(item).split())}_gols_sofridos_como_mandante"] = home_stat.replace(',', '.')
                match_info[f"{'_'.join(remove_accents(item).split())}_gols_sofridos_como_visitante"] = away_stat.replace(',', '.')
                break

    ## From 55 to 58: total number of goals in 1T
    cell_titles = [
        'over 0.5 gols',
        'over 1.5 gols',
        'over 2.5 gols',
    ]
    for i, l in enumerate(remaining[55:58]):
        for item in cell_titles:
            if item in l.lower():
                home_stat, away_stat = get_home_and_away_stats(item, l.lower())
                match_info[f"{'_'.join(remove_accents(item).split())}_gols_in_1T_como_mandante"] = home_stat.replace(',', '.')
                match_info[f"{'_'.join(remove_accents(item).split())}_gols_in_1T_como_visitante"] = away_stat.replace(',', '.')
                break

    ## From 59 to 62: total number of goals in 2T
    cell_titles = [
        'over 0.5 gols',
        'over 1.5 gols',
        'over 2.5 gols',
    ]
    for i, l in enumerate(remaining[55:58]):
        for item in cell_titles:
            if item in l.lower():
                home_stat, away_stat = get_home_and_away_stats(item, l.lower())
                match_info[f"{'_'.join(remove_accents(item).split())}_gols_in_2T_como_mandante"] = home_stat.replace(',', '.')
                match_info[f"{'_'.join(remove_accents(item).split())}_gols_in_2T_como_visitante"] = away_stat.replace(',', '.')
                break

    # from 63 to 70: Tempo dos gols marcados/sofridos
    cell_titles = [
        '00 - 15',
        '16 - 30',
        '31 - 45',
        '46 - 60',
        '61 - 75',
        '76 - 90'
    ]
    for i, l in enumerate(remaining[63:70]):
        for item in cell_titles:
            if item in l.lower():
                modified_item = item.replace(' - ', '-')
                splitting = l.split(item)
                home_goals_timing = splitting[1].strip().split()
                away_goals_timing = splitting[2].strip().split()

                home_goals_scored_in_time_frame = home_goals_timing[0]
                home_goals_against_in_time_frame = home_goals_timing[1]
                home_goals_scored_in_time_frame_percentage = home_goals_timing[2]
                home_goals_against_in_time_frame_percentage = home_goals_timing[3]

                away_goals_scored_in_time_frame = away_goals_timing[0]
                away_goals_against_in_time_frame = away_goals_timing[1]
                away_goals_scored_in_time_frame_percentage = away_goals_timing[2]
                away_goals_against_in_time_frame_percentage = away_goals_timing[3]

                match_info[f'gols_marcados_{modified_item}_como_mandante'] = home_goals_scored_in_time_frame
                match_info[f'gols_sofridos_{modified_item}_como_mandante'] = home_goals_against_in_time_frame
                match_info[f'porcentagem_gols_marcados_{modified_item}_como_mandante'] = home_goals_scored_in_time_frame_percentage
                match_info[f'porcentagem_gols_sofridos_{modified_item}_como_mandante'] = home_goals_against_in_time_frame_percentage

                match_info[f'gols_marcados_{modified_item}_como_visitante'] = away_goals_scored_in_time_frame
                match_info[f'gols_sofridos_{modified_item}_como_visitante'] = away_goals_against_in_time_frame
                match_info[f'porcentagem_gols_marcados_{modified_item}_como_visitante'] = away_goals_scored_in_time_frame_percentage
                match_info[f'porcentagem_gols_sofridos_{modified_item}_como_visitante'] = away_goals_against_in_time_frame_percentage

                break

    # From 72 to 75: Escanteios totais
    cell_titles = [
        'média de cantos a favor',
        'média de cantos contra',
        'média total de cantos',
    ]
    for i, l in enumerate(remaining[72:75]):
        for item in cell_titles:
            if item in l.lower():
                home_stat, away_stat = get_home_and_away_stats(item, l.lower())
                match_info[f"{'_'.join(remove_accents(item).split())}_como_mandante"] = home_stat.replace(',', '.')
                match_info[f"{'_'.join(remove_accents(item).split())}_como_visitante"] = away_stat.replace(',', '.')
                break

    # From 76 to 79: Escanteios 1T
    cell_titles = [
        'média de cantos a favor',
        'ganhou mais de 2 cantos',
        'ganhou mais de 3 cantos',
    ]
    for i, l in enumerate(remaining[76:79]):
        for item in cell_titles:
            if item in l.lower():
                home_stat, away_stat = get_home_and_away_stats(item, l.lower())
                match_info[f"{'_'.join(remove_accents(item).split())}_1T_como_mandante"] = home_stat.replace(',', '.')
                match_info[f"{'_'.join(remove_accents(item).split())}_1T_como_visitante"] = away_stat.replace(',', '.')
                break

    # From 80 to 83: Escanteios 2T
    cell_titles = [
        'média de cantos a favor',
        'ganhou mais de 2 cantos',
        'ganhou mais de 3 cantos',
    ]
    for i, l in enumerate(remaining[80:83]):
        for item in cell_titles:
            if item in l.lower():
                home_stat, away_stat = get_home_and_away_stats(item, l.lower())
                match_info[f"{'_'.join(remove_accents(item).split())}_2T_como_mandante"] = home_stat.replace(',', '.')
                match_info[f"{'_'.join(remove_accents(item).split())}_2T_como_visitante"] = away_stat.replace(',', '.')
                break

    # From 85 to 89: Cartões Média
    cell_titles = [
        'média de cartões recebidos em casa',
        'média total de cartões nos jogos em casa',
        'ganhou mais de 3 cantos',
    ]
    for i, l in enumerate(remaining[80:83]):
        for item in cell_titles:
            if item in l.lower():
                home_stat, away_stat = get_home_and_away_stats(item, l.lower())
                match_info[f"{'_'.join(remove_accents(item).split())}_2T_como_mandante"] = home_stat.replace(',', '.')
                match_info[f"{'_'.join(remove_accents(item).split())}_2T_como_visitante"] = away_stat.replace(',', '.')
                break

    # from 91 to the end: Players info
    players = []
    for i, l in enumerate(remaining[91:]):
        if len(l) > 0 and 'Principais Jogadores' not in l and 'Min/Jogo' not in l:
            player = l.split()
            total_red_cards = player[-1]
            total_yellow_cards = player[-2]
            cards_per_game = player[-3]
            total_cards = player[-4]
            assists = player[-5]
            goals = player[-6]
            average_min_played = player[-7]
            total_min_played = player[-8]
            total_games = player[-9]
            position = player[-10]
            name = ' '.join([re.sub(r'\d+', '', item) for item in player[:-10]])

            player_info = {
                'nome': player,
                'total_cartoes_vermelhos': total_red_cards,
                'total_cartoes_amarelos': total_yellow_cards,
                'cartoes_por_jogo': cards_per_game,
                'total_cartoes': total_cards,
                'assistencias': assists,
                'gols': goals,
                'min_por_jogo': average_min_played,
                'total_min_jogados': total_min_played,
                'jogos totais': total_games,
                'posicao': position,
                'nome': name
            }

            players.append(player_info)

    match_info['players'] = players

    all_matches.append(match_info)

file_name = f"{today_date.day:02d}-{today_date.month:02d}-{today_date.year:04d}"

file_path = f"jsons/{file_name}.json"

with open(file_path, "w", encoding="utf-8") as json_file:
    json.dump(all_matches, json_file, ensure_ascii=False, indent=4)

print('**** FINISHED *****')

