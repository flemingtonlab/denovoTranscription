import sys
import numpy as np
import pyBigWig
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.cluster import KMeans
import random
import glob
import re

# Plot created May 17, 2023
# Any de novo site that had overlap with a blacklisted region (encode) was removed (using the -5000 to +5000 region)

bed_path = '/Users/nate/dnovo/beds/denovo_promoters/de_novo_promoters_Akata_BCR_plus_Mutu_Zta.noblacklist.bed'

basedir = '/Volumes/de_novo/Bisulfite/Akata/coverage/'
uninduced_paths = [basedir + f'{i}.{i}_1_bismark_bt2_pe.deduplicated.bismark.cov.bg.noEBV.bg.bw'  for i in ['C1','C2','C3','C4']]
induced_paths = [basedir + f'{i}.{i}_1_bismark_bt2_pe.deduplicated.bismark.cov.bg.noEBV.bg.bw'  for i in ['Ig1','Ig2','Ig3','Ig4']]


upstream_bases = 5000
downstream_bases = 5000
length = upstream_bases + downstream_bases


def extract_coverage(strand1_paths, regions):
    m = np.zeros([len(regions), length])
    
    for str1_path in strand1_paths:
        str1 = pyBigWig.open(str1_path)
        for ind, region in enumerate(regions):
            start = int(float(region[1]))
            stop = int(float(region[2])) 
            try:
                strand = region[5]
            except:
                strand = '+'
                
            middle = (start + stop) // 2 
            start = middle - upstream_bases
            stop = middle + downstream_bases
            vals = str1.values(region[0], start, stop)
            vals = np.abs(vals)
            #vals = np.nan_to_num(np.array(vals), nan=0)
            if strand == '-':
                vals = np.flip(vals)
            
            m[ind] += vals  
        print(str1_path, "done")
    return m / len(strand1_paths)



def import_bed(path, col_sort=4):
    regions = []
    with open(path) as bed_handle:
        for line in bed_handle:
            regions.append(line.strip('\n').split('\t'))
    random.shuffle(regions)
    regions.sort(key=lambda x: float(x[col_sort]))
    return regions

def plot_heatmap(matrix, name, colormap='Reds',height=8):
    fig = plt.figure(figsize=(3,height))
    plt.imshow(matrix, cmap=colormap,aspect='auto', interpolation="gaussian", vmax=1)
    plt.xticks([])
    plt.yticks([])
    plt.savefig(name + '.heatmap.svg')
    plt.close('all') 

def plot_sumcurves(matrix1, name, color='r',cutoff_number=.0765, binsize=10, max_y=3.5):
    matrix1[matrix1 < cutoff_number] = 0
    matrix1[matrix1 > cutoff_number] = 1
    sums1 = np.sum(matrix1, 0)
    sum_hist1 = [0]
    for i in range(0, len(sums1), binsize):
        sum_hist1.append(np.sum(sums1[i:i+binsize]))
    sum_hist1.append(0)
    fig = plt.figure(figsize=(4,4)) 
    y_vals= np.array(sum_hist1[1:-1]) / matrix1.shape[0]
    plt.plot(y_vals, color=color)
    plt.fill_between(range(len(y_vals)), y_vals, y2=[np.min(y_vals)]*len(y_vals), color=color)
    plt.ylim([np.min(y_vals), max_y])
    plt.yticks([])
    plt.xticks([])
    print(np.max(sum_hist1[1:-1]) / np.shape(matrix1)[0],name)
    plt.savefig(name + '.summation.svg')

def get_zta_sites(denovo_regions):
    zta_vpic_df = pd.read_table('/Users/nate/Downloads/de_novo_promoter_paper/motifs_in_de_novo_promoters/4_vPIC_plus_Zta/4_TATTAAA_TATTTAA_and_Zta_ChIP_seq_Hammerschmidt/TATTAAA_plus_TATTTAA_and_Zta_ChIP_Hammerschmidt_output/de_novo_promoters_Akata_BCR_plus_Mutu_Zta.bed_TATTAAA_plus_TATTTAA.bed.binary_motif_info.bed_Raji_Zta_ChIP_induced_pooledReps_summits.bed.no_EBV_plus_strand.bed.binary_motif_info.tsv', index_col=0)
    zta_vpic_df = zta_vpic_df.set_index('DN prom name')
    zta = zta_vpic_df[zta_vpic_df['Zta_ChIP_Hammerschmidt'] == 1]
    zta = set(zta.index)
    return [i for i in denovo_regions if i[3] in zta]

def get_vpic_sites(denovo_regions):

    bcrf1_motif = "TATT[TA]AA"
    bcrf1_prog = re.compile(bcrf1_motif)
    working_dir = "/Users/nate/Documents/Projects/De_Novo_Promoter/Manuscript/Figures/Figure3/starting_files/"
    fa40_25 = {}
    with open(working_dir + 'de_novo_tss_40to25bp_upstream.allsites.fa') as infile:
        for line in infile:
            line = line.strip('\n')
            if line[0] == '>':
                keya = line.replace('>','').split('(')[0]
            else:
                fa40_25[keya]= line
    return [i for i in denovo_regions if bcrf1_prog.search(fa40_25[i[3]]) is not None]
    
def get_rta_sites(denovo_regions):
        
    fa200_0 = {}
    working_dir = "/Users/nate/Documents/Projects/De_Novo_Promoter/Manuscript/Figures/Figure3/starting_files/"

    with open(working_dir + 'de_novo_tss_200bp_upstream.allsites.fa') as infile:
        for line in infile:
            line = line.strip('\n')
            if line[0] == '>':
                keya = line.replace('>','').split('(')[0]
            else:
                fa200_0[keya]= line
    rta_motif_fw = "G[ACTG]CC[ACGT]{8,10}GG[ACGT]G" 
    rta_motif_rev= "C[ACGT]CC[ACGT]{8,10}GG[ACGT]C"
    rta_prog = re.compile(f'{rta_motif_fw}|{rta_motif_rev}')
    return [i for i in denovo_regions if rta_prog.search(fa200_0[i[3]]) is not None]


def get_sites(denovo_regions):
    rta = get_rta_sites(denovo_regions)
    zta = get_zta_sites(denovo_regions)
    vpic = get_vpic_sites(denovo_regions)
    all_three = rta+zta+vpic
    all_three = [i[3] for i in all_three]

    l = []
    two_plus_sites = []
    for i in all_three:
        if i in l:
            two_plus_sites.append(i)
        l.append(i)

    no_site = [i for i in denovo_regions if i[3] not in all_three]
    vpic = [i for i in vpic if i[3] not in two_plus_sites]
    zta = [i for i in zta if i[3] not in two_plus_sites]
    rta = [i for i in rta if i[3] not in two_plus_sites]
    print(len(rta) + len(zta) + len(vpic) + len(no_site) + len(set(two_plus_sites)), len(denovo_regions))

    return rta, zta, vpic, no_site


def bin(array_2d, bin_size):
    l = []
    for i in range(0, len(array_2d), bin_size):
        l.append(np.mean(array_2d[i:i+bin_size]))
    return l
    


denovo_regions = import_bed(bed_path)
rta, zta, vpic, no_site = get_sites(denovo_regions)

canonical_bed_path = '/Users/nate/TSS_from_akata_uninduced.bed'
canonical = import_bed(canonical_bed_path, col_sort=6)

tpm0 = [i for i in canonical if float(i[6])==0]
tpm3 = [i for i in canonical if float(i[6])>=3]

binsize = 10
xs = [i + binsize/2 for i in range(-upstream_bases, downstream_bases, binsize)]


zta_methyl = bin(np.nanmean(extract_coverage(uninduced_paths, regions=zta), 0), binsize)
rta_methyl = bin(np.nanmean(extract_coverage(uninduced_paths, regions=rta), 0), binsize)
vpic_methyl = bin(np.nanmean(extract_coverage(uninduced_paths, regions=vpic), 0), binsize)
no_site_methyl = bin(np.nanmean(extract_coverage(uninduced_paths, regions=no_site), 0), binsize)
tpm0_methyl = bin(np.nanmean(extract_coverage(uninduced_paths, regions=tpm0), 0), binsize)
tpm3_methyl = bin(np.nanmean(extract_coverage(uninduced_paths, regions=tpm3), 0), binsize)


fig = plt.figure(figsize=(8,8))
ax = plt.subplot()
plt.plot(xs, tpm0_methyl)
plt.plot(xs, tpm3_methyl)
plt.plot(xs, zta_methyl)
ax.set_xticks([-upstream_bases, 0, downstream_bases])
ax.set_yticks([0,25,50,75,100])
plt.ylim([0, 100])
plt.xlim([-upstream_bases, downstream_bases])
plt.axvline(0, ls='--', c='k')
plt.savefig('tpm0_tpm3_zta.methyl.svg')


fig = plt.figure(figsize=(8,8))
ax = plt.subplot()
plt.plot(xs, rta_methyl)
ax.set_xticks([-upstream_bases, 0, downstream_bases])
ax.set_yticks([0,25,50,75,100])
plt.ylim([0, 100])
plt.xlim([-upstream_bases, downstream_bases])
plt.axvline(0, ls='--', c='k')
plt.savefig('rta.methyl.svg')

fig = plt.figure(figsize=(8,8))
ax = plt.subplot()
plt.plot(xs, vpic_methyl)
ax.set_xticks([-upstream_bases, 0, downstream_bases])
ax.set_yticks([0,25,50,75,100])
plt.ylim([0, 100])
plt.xlim([-upstream_bases, downstream_bases])
plt.axvline(0, ls='--', c='k')
plt.savefig('vpic.methyl.svg')

fig = plt.figure(figsize=(8,8))
ax = plt.subplot()
plt.plot(xs, no_site_methyl)
ax.set_xticks([-upstream_bases, 0, downstream_bases])
ax.set_yticks([0,25,50,75,100])
plt.ylim([0, 100])
plt.xlim([-upstream_bases, downstream_bases])
plt.axvline(0, ls='--', c='k')
plt.savefig('no_site.methyl.svg')