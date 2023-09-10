
rule polca:
    input:
        polypolish_fasta = os.path.join(dir.out.polypolish,"{sample}.fasta"),
        polca_fasta = os.path.join(dir.out.polca, "{sample}", "{sample}.fasta")
    output:
        fasta = os.path.join(dir.out.polca,"{sample}", "{sample}.fasta.PolcaCorrected.fa"),
        version = os.path.join(dir.out.versions, "{sample}", "polca_complete.version")
    params:
        #r1 = os.path.join(dir.out.fastp,"{sample}_1.fastq.gz"),
        #r2 = os.path.join(dir.out.fastp,"{sample}_2.fastq.gz"),
        dir = os.path.join(dir.out.polca, "{sample}"),
        reads = ' '.join(os.path.join(dir.out.fastp,"{sample}_1.fastq.gz") os.path.join(dir.out.fastp,"{sample}_2.fastq.gz"))
    conda:
        os.path.join(dir.env,'polca.yaml')
    resources:
        mem_mb=config.resources.med.mem,
        time=config.resources.med.time
    threads:
        config.resources.big.cpu
    shell:
        """
        # real struggle running polca honestly
        cp {input.polypolish_fasta} {input.polca_fasta}
        cd {params.dir}
        polca.sh -a {input.polca_fasta}  -r {params.reads} -t {threads}
        polca.sh --version > {output.version}
        """


rule polca_incomplete:
    input:
        fasta = os.path.join(dir.out.polypolish_incomplete,"{sample}.fasta")
    output:
        fasta = os.path.join(dir.out.polca_incomplete,"{sample}.fasta.PolcaCorrected.fa"),
        version = os.path.join(dir.out.versions, "{sample}", "polca_incomplete.version")
    params:
        r1 = os.path.join(dir.out.fastp,"{sample}_1.fastq.gz"),
        r2 = os.path.join(dir.out.fastp,"{sample}_2.fastq.gz"),
        dir = dir.out.polca_incomplete
    conda:
        os.path.join(dir.env,'polca.yaml')
    resources:
        mem_mb=config.resources.med.mem,
        time=config.resources.med.time
    threads:
        config.resources.big.cpu
    shell:
        """
        # real struggle running polca honestly
        cd {params.dir}
        polca.sh -a {input.fasta}  -r "../../../../{params.r1} ../../../../{params.r2}" -t {threads}
        polca.sh --version > {output.version}
        """






