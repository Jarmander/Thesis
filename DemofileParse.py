import pandas as pd
import numpy as np
from pathlib import Path
from awpy.parser import DemoParser
from itertools import permutations, product


def parse_demofile(demo_path: Path) -> str:
    demo_parser = DemoParser(demofile=demo_path.as_posix(), parse_rate=128)
    data_df = demo_parser.parse(return_type='df')

    rounds_df = data_df['rounds']
    kills_df = data_df['kills']
    damage_df = data_df['damages']
    weapon_df = data_df['weaponFires']
    player_df = data_df['playerFrames']

    ## WEAPON CLASSES
    WEAPON_CLASSES = {'melee': ['Knife'],
                      'pistol': ['CZ75-Auto', 'Desert Eagle', 'Dual Berettas', 'Five-SeveN', 'Glock-18', 'P2000', 'P250', 'R8 Revolver', 'Tec-9', 'USP-S'],
                      'shotgun': ['MAG-7', 'Nova', 'Sawed-Off', 'XM1014'],
                      'machineGun': ['M249', 'Negev'],
                      'smg': ['MAC-10', 'MP5-SD', 'MP7', 'MP9', 'P90', 'PP-Bizon', 'UMP-45'],
                      'rifle': ['AK-47', 'AUG', 'FAMAS', 'Galil AR', 'M4A1-S', 'M4A4', 'SG 553'],
                      'sniper': ['AWP', 'G3SG1', 'SCAR-20', 'SSG 08'],
                      'explosive': ['HE Grenade'],
                      'smoke': ['Smoke Grenade'],
                      'incendiary': ['Incendiary Grenade', 'Molotov'],
                      'flash': ['Flash Grenade'],
                      'decoy': ['Decoy Grenade'],
                      'c4': ['C4']}

    weapons = {}
    for k, v in WEAPON_CLASSES.items():
      for i in v:
        weapons[i] = k

    # Create list of active players per round
    final_df = player_df[['matchID', 'roundNum', 'side', 'name', 'team', 'mapName']].drop_duplicates()
    final_df = final_df.reset_index().drop(['index'], axis=1)

    # Create a DataFrame detailing information about killers and victims
    kill_list = kills_df.loc[:, ['roundNum', 'attackerName', 'victimName', 'weapon', 'tick']]

    # Adjust ticks by round freezetime end tick
    kill_list = kill_list.merge(rounds_df[['roundNum', 'freezeTimeEndTick']], on='roundNum')
    kill_list['tick'] = kill_list['tick'] - kill_list['freezeTimeEndTick']

    final_df = final_df.merge(kill_list[['roundNum', 'victimName', 'tick']],
                                  left_on=['roundNum', 'name'],
                                  right_on=['roundNum', 'victimName'],
                                  how='left')

    # Determine the amount of seconds the surviving players lived
    player_survival_time = rounds_df.loc[:, ['roundNum', 'endTick', 'freezeTimeEndTick']]
    player_survival_time['survivalTime'] = player_survival_time['endTick'] - player_survival_time['freezeTimeEndTick']

    final_df = final_df.merge(player_survival_time, on='roundNum', suffixes=('', '_max'), how='left')

    # Replace NaNs in tick column with maximum survival times
    final_df['tick'].mask(final_df['tick'].isna(), final_df['survivalTime'], inplace=True)

    ## DISTANCE CALCULATIONS
    ## AVERAGE MOVEMENT
    # Calculate average player velocities and set round numbers and names as index
    player_positions = player_df.loc[:, ['roundNum', 'name', 'teamName', 'x', 'y', 'z', 'tick']]
    player_positions = player_positions.set_index(['roundNum', 'name']).sort_index()

    # Copy x, y and z coordinates and shift them up to calculate euclidean distances row wise
    player_positions[['x_copy', 'y_copy', 'z_copy']] = player_positions[['x', 'y', 'z']]
    player_positions[['x_copy', 'y_copy', 'z_copy']] = player_positions[['x_copy', 'y_copy', 'z_copy']].shift(-1)
    player_positions['distance'] = np.sqrt((player_positions['x_copy'] - player_positions['x']) ** 2 +
                                           (player_positions['y_copy'] - player_positions['y']) ** 2 +
                                           (player_positions['z_copy'] - player_positions['z']) ** 2)

    # Retrieve the number of rounds played and unique player names to loop over them
    number_of_rounds = player_positions.reset_index()['roundNum'].iloc[-1]
    player_list = player_positions.reset_index()['name'].unique()

    # Initialize an empty dict and iteratively sum up the total distances traveled by each player every round
    player_distances = {}
    for round, name in list(product(range(1, number_of_rounds + 1), player_list)):
      distance_traveled = player_positions.loc[(round, name), ['distance']].iloc[:-1]
      if round not in player_distances:
        player_distances[round] = {}
      player_distances[round][name] = distance_traveled.groupby(['roundNum', 'name'])['distance'].sum().values[0]
    player_distances_df = pd.DataFrame.from_dict(player_distances).T
    player_distances_df = pd.DataFrame(player_distances_df.stack(), columns=['distance'])
    player_distances_df.index.rename(['roundNum', 'name'], inplace=True)


    ## INTER TEAMMATE DISTANCE
    team_names = player_df['teamName'].unique()
    end_times = rounds_df.loc[:,['roundNum', 'freezeTimeEndTick']].drop_duplicates()
    temp = player_df.merge(end_times, on='roundNum', how='left')
    temp['tick'] = temp['tick'] - temp['freezeTimeEndTick']
    team_1_positions = temp[temp['teamName'] == team_names[0]]
    team_2_positions = temp[temp['teamName'] == team_names[1]]
    team_1_perms = list(permutations(team_1_positions['name'].unique(), 2))
    team_2_perms = list(permutations(team_2_positions['name'].unique(), 2))

    inter_player_positions = temp.loc[:, ['roundNum', 'name', 'x', 'y', 'z', 'tick']].set_index(['roundNum', 'tick', 'name']).unstack()

    player_positions = {}
    for dim in ('x', 'y', 'z'):
      for perm in team_1_perms + team_2_perms:
        player_positions[(f'{dim}_diff', f'{perm[0]}_{perm[1]}')] = (inter_player_positions[(dim, perm[0])] -
                                                                     inter_player_positions[(dim, perm[1])]) ** 2
    inter_player_positions = pd.DataFrame.from_dict(player_positions)
    inter_player_distances = np.sqrt(inter_player_positions['x_diff'] +
                                     inter_player_positions['y_diff'] +
                                     inter_player_positions['z_diff'])

    name_tuples = []
    for pair in inter_player_distances.columns.values:
      name_tuples.append(tuple(pair.split('_')))
    index = pd.MultiIndex.from_tuples(name_tuples)
    inter_player_distances.columns = index

    for round, name in list(product(range(1, number_of_rounds + 1), player_list)):
      criterion = (final_df['roundNum'] == round) & (final_df['name'] == name)
      surv_time = int(final_df[criterion]['tick'].values)
      inter_player_distances.loc[(round, surv_time):(round,), name] = np.nan
      inter_player_distances.loc[(round, surv_time):(round,), (slice(None), name)] = np.nan

    inter_player_distances = inter_player_distances.groupby(axis=1, level=0).mean()
    inter_player_distances = inter_player_distances.groupby('roundNum').sum()
    inter_player_distances = inter_player_distances.unstack().reset_index()
    inter_player_distances.columns = ['name', 'roundNum', 'teamDistance']

    # Calculate the damage every player dealt for each round and merge in to the final DataFrame
    total_damage_dealt = damage_df.loc[:, ['roundNum', 'attackerName', 'victimName', 'armorDamage', 'hpDamage', 'weapon']].groupby(['roundNum', 'attackerName']).sum()

    shots_fired_df = weapon_df.loc[:, ['roundNum', 'playerName','weapon', 'tick']].groupby(['roundNum', 'playerName', 'weapon']).count().unstack()
    shots_fired_df = shots_fired_df.droplevel(0, axis=1)
    shots_fired_df = shots_fired_df.groupby(weapons, axis=1).sum()
    for value in weapons.values():
        if value not in shots_fired_df.columns:
            shots_fired_df[value] = 0.0
    shots_fired_df.columns = [col + 'Fired' for col in shots_fired_df.columns]

    equipment_df = player_df.loc[:, ['roundNum', 'name', 'activeWeapon']].value_counts().sort_index(level=0)
    equipment_df = pd.DataFrame(equipment_df)
    equipment_df = equipment_df.unstack().fillna(0).drop((0, ''), axis=1)
    equipment_df.columns = [col[1] for col in equipment_df.columns]
    equipment_df = equipment_df.groupby(by=weapons, axis=1).sum()
    for value in weapons.values():
        if value not in equipment_df.columns:
            equipment_df[value] = 0.0

    ## MERGE TABLES
    final_df = final_df.merge(player_distances_df, on=['roundNum', 'name'], how='left')
    final_df = final_df.merge(inter_player_distances, on=['roundNum', 'name'], how='left')
    final_df = final_df.merge(equipment_df, on=['roundNum', 'name'], how='left')
    final_df = final_df.merge(shots_fired_df, left_on=['roundNum', 'name'], right_on=['roundNum', 'playerName'], how='left')
    final_df = final_df.merge(total_damage_dealt, left_on=['roundNum', 'name'], right_on=['roundNum', 'attackerName'], how='left')

    ## ADD USEFUL VARIABLES
    # Add dummy variable for survival (True:1/False:0)
    final_df['player_survived'] = np.where(final_df['name'] == final_df['victimName'], 0, 1)

    final_df['avgTeamDistance'] = final_df['teamDistance'] / final_df['tick']
    final_df['avgMovement'] = final_df['distance'] / final_df['tick']

    final_df.drop('victimName', axis=1, inplace=True)
    final_df.fillna(0, inplace=True)

    return final_df.to_csv()