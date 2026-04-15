# Conflict Detection Comparison

| Exp | Scenario | Ordering | Git | SHACL | Oracle | Valid |
|:---:|----------|----------|:---:|:-----:|:------:|:----:|
| 14 | true-negative | a-into-b | no | no | no | yes |
| 14 | true-negative | b-into-a | no | no | no | yes |
| 14 | false-negative | a-into-b | no | no | yes | no |
| 14 | false-negative | b-into-a | no | no | yes | no |
| 14 | true-positive | a-into-b | yes | — | — | — |
| 14 | true-positive | b-into-a | yes | — | — | — |
| 14 | false-positive | a-into-b | yes | — | — | — |
| 14 | false-positive | b-into-a | yes | — | — | — |
| 15 | benign | composed | no | no | no | yes |
| 15 | property-rename | composed | no | yes | no | no |
| 15 | constraint-data | composed | no | yes | no | no |
| 17 | benign | a-into-b | no | no | no | yes |
| 17 | benign | b-into-a | no | no | no | yes |
| 17 | coupling | a-into-b | no | no | yes | no |
| 17 | coupling | b-into-a | no | no | yes | no |
| 17 | ordering | a-then-b (seque | yes | no | yes | no |
| 17 | ordering | b-then-a (seque | yes | no | no | yes |
| 17 | textual | a-into-b | yes | — | — | — |
| 17 | textual | b-into-a | yes | — | — | — |
