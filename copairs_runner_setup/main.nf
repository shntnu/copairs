nextflow.enable.dsl = 2
params.jobs_yaml = 'conf/jobs_list.yaml'

Channel
    .fromPath(params.jobs_yaml)
    .map { yaml ->
        def txt = "python - <<'PY'\nimport yaml, json, sys, pathlib; " +
                  "import yaml as y; print('\\n'.join(json.dumps(j) " +
                  "for j in y.safe_load(open(sys.argv[1]))['jobs']))\nPY\n${yaml}"
        txt.execute().text.readLines()
    }
    .flatten()
    .map { line -> groovy.json.JsonSlurper.newInstance().parseText(line) }
    .set { JOBS }

process copairs {
    tag   { job.name }
    input:
      val job from JOBS
    script:
      """
      python -m copairs_runner.cli ${ job.overrides.join(' ') }
      """
}
