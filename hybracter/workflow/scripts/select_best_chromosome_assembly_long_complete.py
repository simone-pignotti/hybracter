#!/usr/bin/env python3

import os
import sys

import pandas as pd
import pyrodigal
from Bio import SeqIO


# determines whether a file is empty
def is_file_empty(file):
    """
    Determines if file is empty
    :param file: file path
    :return: empty Boolean
    """
    empty = False
    if os.stat(file).st_size == 0:
        empty = True
    return empty


def calculate_mean_CDS_length(filepath_in):
    """
    calculates the mean CDS length in a fasta file and returns it as a float

    :param filepath_in: The path to the input FASTA file.
    :return: The mean length of sequences in the FASTA file as a float.
    """

    prodigal_metamode = False
    coding_table = 11

    # for training if you want different coding table
    seqs = [bytes(record.seq) for record in SeqIO.parse(filepath_in, "fasta")]
    record = SeqIO.parse(filepath_in, "fasta")

    # train pyrodigal
    orf_finder = pyrodigal.GeneFinder(meta=prodigal_metamode)
    trainings_info = orf_finder.train(*seqs, translation_table=int(coding_table))
    orf_finder = pyrodigal.GeneFinder(trainings_info, meta=prodigal_metamode)

    # run pyrodigal

    total_genes = 0
    total_length = 0

    for i, record in enumerate(SeqIO.parse(filepath_in, "fasta")):
        genes = orf_finder.find_genes(str(record.seq))
        for gene in genes:
            total_genes += 1
            total_length += len(gene.sequence())  # add the length of the gene called

    mean_cds_len = float(total_length / total_genes)
    mean_cds_len = float("{:.2f}".format(mean_cds_len))

    return mean_cds_len


def select_best_chromosome_assembly_long_complete(
    hybracter_summary,
    pyrodigal_summary,
    final_plasmid_fasta,
    output_chromosome_fasta,
    overall_output_fasta,
    chrom_pre_polish_fasta,
    medaka_rd_1_fasta,
    medaka_rd_2_fasta,
    sample,
    flye_info
):
    """
    get prodigal mean length for each chromosome
    Then creates summary tsv
    statistics similar to unicycler
    instead of 1,2,3 etc we will use 'chromosome00001', 'chromosome00002' etc (for edge cases of multiple chroms/megaplasmids chromids etc)
    Then it reads the plassembler output
    Checks if not empty
    And if it isn't, then adds plassembler contigs to the final output
    Then creates hybracter_summary tsv
    """

    # get mean CDS lengths
    chrom_pre_polish_mean_cds = calculate_mean_CDS_length(chrom_pre_polish_fasta)
    medaka_rd_1_mean_cds = calculate_mean_CDS_length(medaka_rd_1_fasta)
    medaka_rd_2_mean_cds = calculate_mean_CDS_length(medaka_rd_2_fasta)

    # create dict with mean CDS lengths
    dict = {
        "Sample": sample,
        "pre_polish_mean_cds_length": chrom_pre_polish_mean_cds,
        "medaka_rd_1_mean_cds_length": medaka_rd_1_mean_cds,
        "medaka_rd_2_mean_cds_length": medaka_rd_2_mean_cds,
    }

    # Convert the dictionary to a DataFrame
    summary_df = pd.DataFrame([dict])

    # Write to a tsv file
    summary_df.to_csv(pyrodigal_summary, index=False, sep="\t")

    # determine the best assembly
    best_assembly = medaka_rd_2_fasta
    best_round = "medaka_rd_2"

    if (
        medaka_rd_1_mean_cds > medaka_rd_2_mean_cds
        and chrom_pre_polish_mean_cds < medaka_rd_1_mean_cds
    ):
        best_assembly = medaka_rd_1_fasta
        best_round = "medaka_rd_1"

    if (
        medaka_rd_1_mean_cds > medaka_rd_2_mean_cds
        and medaka_rd_1_mean_cds < chrom_pre_polish_mean_cds
    ):
        best_assembly = chrom_pre_polish_fasta
        best_round = "pre_polish"

    # write the chromosome(s)
    # usually should be 1!
    number_of_chromosomes = sum(1 for _ in SeqIO.parse(best_assembly, "fasta"))
    if number_of_chromosomes <= 0:
        sys.exit(f"The assembly FASTA {best_assembly} is empty.")

    # in case there is multiple - counter
    chromosomes = 1

    # instantiate longest contig length
    longest_contig_length = 0

    # total assembly length
    total_assembly_length = 0

    # Open the output file in write mode
    with open(output_chromosome_fasta, "w") as output_handle:
        with open(overall_output_fasta, "w") as output_handle_overall:
            # Iterate through the records in the best assembly FASTA file and write them to the output file
            for record in SeqIO.parse(best_assembly, "fasta"):
                # to match the 00001 output favoured generally for parsing
                # usually there will be 1 chromosome of course!
                record.id = f"chromosome{chromosomes:05}"

                # Calculate the length of the sequence
                sequence_length = len(record.seq)

                # total assembly length
                total_assembly_length += sequence_length

                # to get longest contig
                if chromosomes == 1:
                    longest_contig_length = sequence_length
                else:
                    if sequence_length > longest_contig_length:
                        longest_contig_length = sequence_length

                # Update the description (header) with the length information
                record.description = f"len={sequence_length}"

                # Write the modified record to the output file
                SeqIO.write(record, output_handle, "fasta")
                SeqIO.write(record, output_handle_overall, "fasta")

    #######################
    # plasmid
    #######################

    # set counter to 0 for number of plasmids
    plasmids = 0
    circular_plasmids = 0

    if (
        is_file_empty(final_plasmid_fasta) is False
    ):  # if the plassembler output is not empty
        # Open the output file in write mode
        with open(
            overall_output_fasta, "a"
        ) as output_handle_overall:  # needs to be append
            # Iterate through the records in the best assembly FASTA file and write them to the output file
            for record in SeqIO.parse(final_plasmid_fasta, "fasta"):
                plasmids += 1

                # the header is already done
                # add record length
                total_assembly_length += len(record.seq)

                if "circular" in record.description:
                    circular_plasmids += 1

                # take description from plassembler (length and copy number)
                # Write the modified record to the output file
                SeqIO.write(record, output_handle_overall, "fasta")
    else:
        plasmids = 0  # do nothing as file is empty
        circular_plasmids = 0

    number_of_contigs = chromosomes + plasmids

    # read in the flye info and extract longest contig
    flye_df = pd.read_csv(flye_info, sep='\t')

    # Find the row with the largest length.
    longest_contig_row = flye_df[flye_df['length'] == flye_df['length'].max()]

    # Extract the coverage value from the longest contig row.
    longest_contig_coverage = longest_contig_row['cov.'].values[0]

    # to get the summary df
    summary_dict = {
        "Sample": sample,
        "Complete": "True",
        "Total_assembly_length": total_assembly_length,
        "Number_of_contigs": number_of_contigs,
        "Most_accurate_polishing_round": best_round,
        "Longest_contig_length": longest_contig_length,
        "Longest_contig_coverage": longest_contig_coverage,
        "Number_circular_plasmids": int(circular_plasmids),
    }

    # Create a DataFrame from the dictionary
    summary_df = pd.DataFrame([summary_dict])
    summary_df.to_csv(hybracter_summary, index=False, sep="\t")


select_best_chromosome_assembly_long_complete(
    snakemake.output.hybracter_summary,
    snakemake.output.pyrodigal_summary,
    snakemake.input.final_plasmid_fasta,
    snakemake.output.chromosome_fasta,
    snakemake.output.total_fasta,
    snakemake.input.chrom_pre_polish_fasta,
    snakemake.input.medaka_rd_1_fasta,
    snakemake.input.medaka_rd_2_fasta,
    snakemake.wildcards.sample,
    snakemake.input.flye_info
)
