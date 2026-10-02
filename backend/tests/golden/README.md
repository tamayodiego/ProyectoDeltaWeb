# Golden master de la app de escritorio (Java)

Copia de `ProyectoDelta/src/test/resources/golden/`. Son los resultados de referencia
que la versión en Python debe reproducir en la Fase 1. **No editar a mano.**

| Archivo | Casos | Notas |
|---|---|---|
| `grupoA_n1-11.txt` | 132 (n = 1..11, 3 semillas) | Referencia confiable |
| `grupoB_n12-15.txt` | 32 (n = 12..15, 2 semillas) | Generado ya con el determinante exacto (Bareiss) |

Cada caso combina `n`, tipo de matriz (`SIM` simétrica 0/1, `ANTI` antisimétrica -1/0/1),
campo (`GF2`, `GF3`) y semilla. Una línea por caso, campos separados por ` | `:

```
n=2 tipo=ANTI campo=GF2 semilla=1 | matriz=0,1;-1,0 | toString=2 Factibles en GF(2) | familia=2 sha=4162cbb1ea78664c | huella=(1,0,1) | frecuencias=[1, 1] | determinantes sha=080a9ed428559ef6
```

| Campo | Significado | Cómo compararlo desde Python |
|---|---|---|
| `matriz` | Filas separadas por `;`, entradas por `,` | Entrada directa: no hace falta reproducir el generador aleatorio de Java |
| `familia=N` | Número de factibles (incluye el vacío) | Directo |
| `huella` | Factibles por cardinalidad, de 0 a n | Directo |
| `frecuencias` | En cuántos factibles aparece cada elemento | Directo |
| `familia ... sha` | Primeros 16 hex del SHA-256 de `Familia.toString()` de Java | Solo si se reproduce el orden y formato exactos de la lista de Java |
| `determinantes sha` | Igual, sobre la lista de determinantes de los factibles | Ídem |

Pendiente para la Fase 1: los dos `sha` dependen del orden interno de las listas de
Java. Si reproducirlo resulta frágil, la opción recomendada es regenerar desde Java un
golden extendido con la familia completa (cada factible escrito explícitamente), para
comparar como conjuntos.
