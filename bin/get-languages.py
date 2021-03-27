from time import sleep
from jug.utils import identity
import json
import pandas as pd
from jug import TaskGenerator
import requests

BASE_GH_API_URL = 'https://api.github.com/'

INEXISTENT = set([
    ('velten', 'STEMNET'),
    ('wiki', 'cn.mops'),
    ])

@TaskGenerator
def get_languages(owner, repo):
    if (owner, repo) in INEXISTENT:
        return b'{}'
    r = requests.get(f'{BASE_GH_API_URL}repos/{owner}/{repo}/languages', params={'Accept': "application/vnd.github.v3+json"})
    if r.status_code != 200:
        print(f"FAILED {owner}/{repo}")
        raise IOError(str(r))
    sleep(64) # API limit is 60 per hour, so we throttle heavily here
    return r.content

@TaskGenerator
def plot_stats(languages, data):
    import json
    from matplotlib import pyplot as plt
    import seaborn as sns
    from scipy import stats

    languages = {ix:pd.Series(json.loads(v)) for ix,v in languages.items()}
    languages = pd.DataFrame(languages).fillna(0).astype(int)
    data['main_language'] = languages.drop(['TeX', 'HTML', 'Rich Text Format', 'Groff', 'Roff']).idxmax()
    data = data.loc[data['main_language'].dropna().index]
    speed = pd.read_table('../data/meanRankSpeedData.tsv')
    merged = pd.merge(data, speed, how='inner', left_on='tool', right_on='method')
    # Get the languages with at least 10 rows
    use_count = merged['main_language'].value_counts().sort_values()
    lang_order = use_count[use_count >= 10][::-1].index
    with open('../manuscript/programming-languages-stats.txt', 'wt') as out:
        out.write("SPEED\n")
        out.write(str(merged.groupby('main_language').describe().speedRank.sort_values(by='mean').query('count >= 10')))
        out.write("\n{}".format(
            stats.kruskal(*[merged.loc[merged['main_language'] == ell]['speedRank'].values for ell in lang_order])))
        out.write("\n\n")
        out.write("ACCURACY\n")
        out.write(str(merged.groupby('main_language').describe().accuracyRank.sort_values(by='mean').query('count >= 10')))
        out.write("\n{}".format(
            stats.kruskal(*[merged.loc[merged['main_language'] == ell]['accuracyRank'].values for ell in lang_order])))
        out.write("\n")


    fig,axes = plt.subplots(2,1)


    sns.boxplot(x='main_language', order=lang_order, y ='speedRank', data=merged, ax=axes[1])
    sns.boxplot(x='main_language', order=lang_order, y ='accuracyRank', data=merged, ax=axes[0])
    fig.tight_layout()
    fig.savefig('../figures/programming-languages.svg')
    fig.savefig('../figures/programming-languages.pdf')



data = pd.read_table('../data/speed-vs-accuracy-toolInfo2005-2020.tsv')
languages = {}
for ix,row in data.iterrows():
    gh = row['Github repo']
    if pd.isna(gh):
        continue
    toks = gh.rstrip('/').split('/')
    owner,repo = toks[-2:]
    languages[ix] = get_languages(owner, repo)

plot_stats(languages, data)
