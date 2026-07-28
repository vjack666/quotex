# Estocástico en zona OS/OB — estudio empírico (EURUSD M15, 14 años)

Ventana: 200,000 velas M15 (datos SMC prestados, read-only).
Umbrales: OS<= 20 | OB>= 80 | pegadas |K-D|<=2
          | separadas |K-D|>= 5 | despegue a 10 velas >= 15 pip

## Tu secuencia, con números

1. Velas en zona (OS o OB): **75,712** de 200,000 (37.9%)
2. De esas, con líneas SEPARADAS de verdad: **10,609**
   (5.3% del total)
3. Cruces totales de %K/%D: **49,161**
4. Cruces OCURRIENDO en zona + separadas (el setup de tu teoría): **1,207**
5. De esos setups, los que tuvieron DESPEGUE de precio real: **296**
   -> **tasa de despegue = 24.5%**

## Desglose por zona

- Sobreventa (OS): 9,791 setups, 137 despegues -> 1.4%
- Sobrecompra (OB): 10,261 setups, 159 despegues -> 1.5%

## Lectura

Si la tasa de despegue es claramente > 50% en una zona, tu teoría del
"despegue tras líneas separadas en zona" QUEDA REGISTRADA CON NÚMEROS.
Si está cerca de 50%, el despegue es azar (las líneas separadas no predicen
dirección). El CSV por vela permite auditar cada evento.
