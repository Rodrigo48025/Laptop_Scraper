import re
from typing import Dict, Any, Optional
try:
    from power_utils import calculate_power_specs
except ImportError:
    from .power_utils import calculate_power_specs

def analyze_cpu(cpu_str: Optional[str], title_str: str = "", text_str: str = "") -> Dict[str, Any]:
    """
    Comprehensive, deterministic CPU hardware comparator and analyzer.
    Maps processors to equivalencies across Intel, AMD, Apple Silicon, and Qualcomm Snapdragon,
    with core topology, benchmark estimates, and plain-language engineering explanations.
    """
    full_text = f"{title_str} {cpu_str or ''} {text_str}".lower()

    # Default fallback
    result = {
        "model_name": cpu_str or "Processador Multi-Core",
        "family": "Genérico",
        "generation": "Padrão",
        "release_year": 2021,
        "cores_threads": "4 a 8 Núcleos",
        "architecture_nm": "10nm / 7nm",
        "passmark_score": 14000,
        "compute_tier": 60,
        "single_core_tier": 60,
        "equivalents": {
            "intel": "Intel Core i5 (11ª/12ª Geração)",
            "amd": "AMD Ryzen 5 (série 5000)",
            "apple": "Apple M1 (base)",
            "snapdragon": "Snapdragon X Plus"
        },
        "engineer_summary": "Processador com desempenho equilibrado para tarefas diárias, desenvolvimento web e execução de código padrão.",
        "strengths": ["Baixo consumo", "Suficiente para terminal e compilações médias"]
    }

    # 1. Intel Core Ultra (Meteor Lake / Arrow Lake)
    if "core ultra" in full_text or "ultra 7" in full_text or "ultra 5" in full_text:
        is_ultra_7 = "ultra 7" in full_text or "155h" in full_text or "165h" in full_text
        if is_ultra_7:
            result.update({
                "model_name": "Intel Core Ultra 7 155H",
                "family": "Intel Core Ultra",
                "generation": "Meteor Lake (Intel 4 - 7nm EUV)",
                "release_year": 2024,
                "cores_threads": "16 Núcleos (6P + 8E + 2LP) / 22 Threads",
                "architecture_nm": "Intel 4 (7nm EUV)",
                "passmark_score": 25500,
                "compute_tier": 92,
                "single_core_tier": 90,
                "equivalents": {
                    "intel": "Intel Core i7-13700H (desempenho similar com NPU IA dedicada)",
                    "amd": "AMD Ryzen 7 7840HS / Ryzen 7 8845HS (Zen 4)",
                    "apple": "Apple M3 (Proximo em multi-core, ganha em flexibilidade x86)",
                    "snapdragon": "Qualcomm Snapdragon X Elite (X1E-78-100)"
                },
                "engineer_summary": "Arquitetura topo de gama de 2024 com NPU integrada para aceleração de IA. 16 núcleos físicos perfeitos para compilações paralelas pesadas, dezenas de containers Docker e virtualização KVM.",
                "strengths": ["NPU Intel AI Boost", "16 Núcleos físicos", "iGPU Intel Arc topo de gama", "Excelente eficiência energética"]
            })
        else:
            result.update({
                "model_name": "Intel Core Ultra 5 125H",
                "family": "Intel Core Ultra",
                "generation": "Meteor Lake (Intel 4)",
                "release_year": 2024,
                "cores_threads": "14 Núcleos (4P + 8E + 2LP) / 18 Threads",
                "architecture_nm": "Intel 4 (7nm EUV)",
                "passmark_score": 21800,
                "compute_tier": 84,
                "single_core_tier": 85,
                "equivalents": {
                    "intel": "Intel Core i5-13500H",
                    "amd": "AMD Ryzen 5 7640HS / Ryzen 7 7735HS",
                    "apple": "Apple M2",
                    "snapdragon": "Snapdragon X Plus"
                },
                "engineer_summary": "Processador ultramoderno de 14 núcleos com NPU de IA integrada. Ideal para trabalho remoto intensivo, compilação e autonomia de bateria.",
                "strengths": ["NPU de IA", "14 Núcleos híbridos", "Gráfica Intel Arc integrada"]
            })
        return result

    # 2. AMD Ryzen 7 7840HS / 7840U / 8845HS (Zen 4)
    if any(x in full_text for x in ["7840hs", "7840u", "7840", "8845hs", "8840"]):
        result.update({
            "model_name": "AMD Ryzen 7 7840HS (Zen 4)",
            "family": "AMD Ryzen 7",
            "generation": "Zen 4 Phoenix (4nm TSMC)",
            "release_year": 2023,
            "cores_threads": "8 Núcleos de Alta Performance / 16 Threads",
            "architecture_nm": "4nm FinFET",
            "passmark_score": 28800,
            "compute_tier": 96,
            "single_core_tier": 94,
            "equivalents": {
                "intel": "Intel Core i7-13700H / Core Ultra 7 155H",
                "amd": "AMD Ryzen 9 7940HS / Ryzen 7 8845HS",
                "apple": "Apple M3 Pro (empate técnico em multi-core sustentado)",
                "snapdragon": "Qualcomm Snapdragon X Elite (X1E-80-100)"
            },
            "engineer_summary": "Monstro de eficiência construído no nó de 4nm da TSMC. Todos os 8 núcleos são de alta velocidade (sem núcleos lentos de eficiência). Ideal para compilações pesadas C++/Rust/Go e suporte avançado de virtualização AMD-V.",
            "strengths": ["8 Núcleos 'P' completos em 4nm", "Gráfica integrada Radeon 780M (a mais rápida)", "Ryzen AI NPU nativa", "Altíssima eficiência térmica"]
        })
        return result

    # 3. Intel 13ª / 14ª Geração (i7-13620H, i7-13700H, i5-13500H)
    if any(x in full_text for x in ["13620h", "13700h", "13500h", "13420h", "13650hx", "14700hx", "1335u", "1345u", "13500"]):
        if any(x in full_text for x in ["13700h", "14700", "13650"]):
            result.update({
                "model_name": "Intel Core i7-13700H",
                "family": "Intel Core i7",
                "generation": "13ª Geração Raptor Lake (Intel 7 - 10nm)",
                "release_year": 2023,
                "cores_threads": "14 Núcleos (6P + 8E) / 20 Threads",
                "architecture_nm": "Intel 7 (10nm SuperFin)",
                "passmark_score": 27500,
                "compute_tier": 95,
                "single_core_tier": 95,
                "equivalents": {
                    "intel": "Intel Core i9-12900H / Core Ultra 7 155H",
                    "amd": "AMD Ryzen 7 7840HS / Ryzen 9 6900HX",
                    "apple": "Apple M2 Pro / M3",
                    "snapdragon": "Snapdragon X Elite"
                },
                "engineer_summary": "14 núcleos com velocidade turbo até 5.0 GHz. Excelente poder bruto para compilação paralela de código e execução de máquinas virtuais.",
                "strengths": ["20 Threads de execução", "Turbo até 5.0 GHz", "Instruções AVX2 e Intel QuickSync"]
            })
        elif "13620h" in full_text or "13620" in full_text:
            result.update({
                "model_name": "Intel Core i7-13620H",
                "family": "Intel Core i7",
                "generation": "13ª Geração Raptor Lake (Intel 7 - 10nm)",
                "release_year": 2023,
                "cores_threads": "10 Núcleos (6P + 4E) / 16 Threads",
                "architecture_nm": "Intel 7 (10nm SuperFin)",
                "passmark_score": 25800,
                "compute_tier": 92,
                "single_core_tier": 94,
                "equivalents": {
                    "intel": "Intel Core i7-12700H / Core i5-13500H",
                    "amd": "AMD Ryzen 7 7735HS / Ryzen 7 5800H (muito superior em single-core)",
                    "apple": "Apple M2 (superior em multi-core, ~igual em single-core)",
                    "snapdragon": "Snapdragon X Plus / X Elite"
                },
                "engineer_summary": "Processador moderno de 10 núcleos com clock turbo a 4.9 GHz. Os 6 núcleos de Performance garantem tempos mínimos de compilação, enquanto os 4 núcleos de Eficiência tratam de daemons de fundo e SSH.",
                "strengths": ["6 Núcleos P de alta velocidade (4.9 GHz)", "16 Threads", "Instruções AVX2 para matemática e IA", "Suporte nativo DDR4 e DDR5"]
            })
        elif "13500h" in full_text or "13500" in full_text or "15 13500h" in full_text:
            result.update({
                "model_name": "Intel Core i5-13500H",
                "family": "Intel Core i5",
                "generation": "13ª Geração Raptor Lake (Intel 7 - 10nm)",
                "release_year": 2023,
                "cores_threads": "12 Núcleos (4P + 8E) / 16 Threads",
                "architecture_nm": "Intel 7 (10nm SuperFin)",
                "passmark_score": 23200,
                "compute_tier": 88,
                "single_core_tier": 91,
                "equivalents": {
                    "intel": "Intel Core i7-12650H / Core i5-12500H",
                    "amd": "AMD Ryzen 7 5800H / Ryzen 5 7640HS",
                    "apple": "Apple M2 (base)",
                    "snapdragon": "Snapdragon X Plus"
                },
                "engineer_summary": "12 núcleos físicos num i5 moderno. Supera processadores i7 de gerações anteriores em eficiência e capacidade multi-thread para Docker e desenvolvimento.",
                "strengths": ["12 Núcleos físicos", "Frequência turbo rápida", "Baixo consumo relativo"]
            })
        else:
            result.update({
                "model_name": "Intel Core 13ª Geração",
                "family": "Intel Core",
                "generation": "13ª Geração Raptor Lake",
                "release_year": 2023,
                "cores_threads": "8 a 10 Núcleos Híbridos",
                "architecture_nm": "10nm",
                "passmark_score": 19500,
                "compute_tier": 78,
                "single_core_tier": 88,
                "equivalents": {
                    "intel": "Intel Core i7 12ª Gen",
                    "amd": "AMD Ryzen 5 5600H / 7530U",
                    "apple": "Apple M1",
                    "snapdragon": "Snapdragon X Plus"
                },
                "engineer_summary": "Excelente arquitetura moderna com suporte completo para Debian/Ubuntu, Docker e ferramentas de engenharia.",
                "strengths": ["Arquitetura moderna", "Excelente responsividade"]
            })
        return result

    # 4. AMD Ryzen 7 5800H / 5800HS / 5700U / 6800H / 7730U (Zen 3 / Zen 3+)
    if any(x in full_text for x in ["5800h", "5800hs", "5800", "6800h", "6800u", "7735u", "7735hs", "5825u", "5700u", "7730u", "7730"]):
        is_6800 = any(x in full_text for x in ["6800h", "6800u", "7735"])
        if is_6800:
            result.update({
                "model_name": "AMD Ryzen 7 6800H / 7735HS (Zen 3+)",
                "family": "AMD Ryzen 7",
                "generation": "Zen 3+ Rembrandt (6nm TSMC)",
                "release_year": 2022,
                "cores_threads": "8 Núcleos / 16 Threads",
                "architecture_nm": "6nm TSMC",
                "passmark_score": 24000,
                "compute_tier": 89,
                "single_core_tier": 87,
                "equivalents": {
                    "intel": "Intel Core i7-12700H / Core i5-13500H",
                    "amd": "AMD Ryzen 7 7735HS",
                    "apple": "Apple M1 Pro / M2",
                    "snapdragon": "Snapdragon X Plus"
                },
                "engineer_summary": "8 núcleos potentes em 6nm com gráfica Radeon 680M RDNA2. Combinação fantástica para compilação, virtualização e baixo consumo de energia.",
                "strengths": ["8 Núcleos / 16 Threads Zen 3+", "Gráfica integrada Radeon 680M rápida", "Excelente autonomia"]
            })
        elif "7730u" in full_text or "7730" in full_text or "5825u" in full_text:
            result.update({
                "model_name": "AMD Ryzen 7 7730U (Zen 3 - 8C/16T)",
                "family": "AMD Ryzen 7",
                "generation": "Zen 3 Barcelo-R (7nm TSMC)",
                "release_year": 2023,
                "cores_threads": "8 Núcleos / 16 Threads (15W)",
                "architecture_nm": "7nm TSMC",
                "passmark_score": 19200,
                "compute_tier": 81,
                "single_core_tier": 82,
                "equivalents": {
                    "intel": "Intel Core i5-12450H / Core i7-1255U",
                    "amd": "AMD Ryzen 7 5825U / Ryzen 5 7640HS",
                    "apple": "Apple M1",
                    "snapdragon": "Snapdragon X Plus"
                },
                "engineer_summary": "8 núcleos físicos e 16 threads em arquitetura Zen 3 pura a 15W. Perfeito para trabalho de programação diário, compilação paralela rápida e grande autonomia de bateria sem ventoinhas audíveis.",
                "strengths": ["8 Núcleos Zen 3 a 15W", "16 Threads para multitarefa", "Muito silencioso e eficiente"]
            })
        elif "5800h" in full_text or "5800" in full_text:
            result.update({
                "model_name": "AMD Ryzen 7 5800H (Zen 3)",
                "family": "AMD Ryzen 7",
                "generation": "Zen 3 Cezanne (7nm TSMC)",
                "release_year": 2021,
                "cores_threads": "8 Núcleos Completos / 16 Threads",
                "architecture_nm": "7nm TSMC",
                "passmark_score": 21300,
                "compute_tier": 85,
                "single_core_tier": 83,
                "equivalents": {
                    "intel": "Intel Core i7-11800H ou Intel Core i5-12500H",
                    "amd": "AMD Ryzen 9 5900HX (muito próximo)",
                    "apple": "Apple M1 Pro (8-Core) em multi-core",
                    "snapdragon": "Qualcomm Snapdragon X Plus (X1P-64-100)"
                },
                "engineer_summary": "Um dos processadores de engenharia mais fiáveis e equilibrados de sempre. 8 núcleos físicos idênticos de alta performance sem throttling agressivo. Excelente para compilação paralela contínua e VMs KVM.",
                "strengths": ["8 Núcleos x86_64 simétricos", "Estabilidade térmica comprovada", "Zero incompatibilidades com Linux/Debian"]
            })
        else: # 5700U
            result.update({
                "model_name": "AMD Ryzen 7 5700U (8C/16T)",
                "family": "AMD Ryzen 7",
                "generation": "Zen 2 / Lucienne (7nm)",
                "release_year": 2021,
                "cores_threads": "8 Núcleos / 16 Threads (15W)",
                "architecture_nm": "7nm",
                "passmark_score": 15800,
                "compute_tier": 73,
                "single_core_tier": 72,
                "equivalents": {
                    "intel": "Intel Core i7-1165G7 / Core i5-1235U",
                    "amd": "AMD Ryzen 5 5600U",
                    "apple": "Apple M1 (base)",
                    "snapdragon": "Snapdragon 8cx Gen 3"
                },
                "engineer_summary": "8 núcleos físicos de baixo consumo (15W). Bateria fantástica, excelente para programação remota, containers leves e escritório sem ruído de ventoinhas.",
                "strengths": ["8 Núcleos a apenas 15W TDP", "Silencioso e fresco", "16 Threads"]
            })
        return result

    # 5. Intel 12ª Geração (i7-12700H, i5-12500H, i5-12450H, i5-1235U)
    if any(x in full_text for x in ["12700h", "12500h", "12450h", "12800h", "12650h", "1235u", "1245u", "1255u", "1240p"]):
        if any(x in full_text for x in ["12700h", "12800h"]):
            result.update({
                "model_name": "Intel Core i7-12700H",
                "family": "Intel Core i7",
                "generation": "12ª Geração Alder Lake (Intel 7 - 10nm)",
                "release_year": 2022,
                "cores_threads": "14 Núcleos (6P + 8E) / 20 Threads",
                "architecture_nm": "Intel 7 (10nm)",
                "passmark_score": 26400,
                "compute_tier": 93,
                "single_core_tier": 92,
                "equivalents": {
                    "intel": "Intel Core i7-13620H / Core i9-11980HK",
                    "amd": "AMD Ryzen 7 6800H / Ryzen 7 7735HS",
                    "apple": "Apple M1 Max / M2 Pro",
                    "snapdragon": "Snapdragon X Elite"
                },
                "engineer_summary": "Potência bruta de 14 núcleos. Lida sem esforço com compilações gigantes, clusters locais de microserviços e emuladores pesados.",
                "strengths": ["20 Threads", "Excelente largura de banda de memória", "Suporte DDR5 e PCIe Gen 4"]
            })
        elif any(x in full_text for x in ["12500h", "12450h", "1240p"]):
            result.update({
                "model_name": "Intel Core i5-12500H",
                "family": "Intel Core i5",
                "generation": "12ª Geração Alder Lake (Intel 7)",
                "release_year": 2022,
                "cores_threads": "12 Núcleos (4P + 8E) / 16 Threads",
                "architecture_nm": "Intel 7 (10nm)",
                "passmark_score": 21500,
                "compute_tier": 85,
                "single_core_tier": 89,
                "equivalents": {
                    "intel": "Intel Core i7-11800H (supera em single-core)",
                    "amd": "AMD Ryzen 7 5800H (empate em multi-core, mais rápido em single)",
                    "apple": "Apple M1 / M2",
                    "snapdragon": "Snapdragon X Plus"
                },
                "engineer_summary": "Um dos melhores 'sweet spots' da Intel. 12 núcleos físicos que batem quase todos os i7 de 10ª e 11ª geração com facilidade.",
                "strengths": ["12 Núcleos", "Excelente relação preço/desempenho", "Instruções modernas"]
            })
        else: # 1235U / 1255U
            result.update({
                "model_name": "Intel Core 12ª Geração Série U (10 Cores)",
                "family": "Intel Core",
                "generation": "12ª Geração Alder Lake (15W)",
                "release_year": 2022,
                "cores_threads": "10 Núcleos (2P + 8E) / 12 Threads",
                "architecture_nm": "Intel 7 (10nm)",
                "passmark_score": 13600,
                "compute_tier": 68,
                "single_core_tier": 82,
                "equivalents": {
                    "intel": "Intel Core i7-1165G7 / Core i5-1135G7",
                    "amd": "AMD Ryzen 5 5500U",
                    "apple": "Apple M1 (base)",
                    "snapdragon": "Snapdragon 8cx Gen 3"
                },
                "engineer_summary": "Processador ultraleve para portáteis finos. Muito rápido em tarefas comuns de desktop e excelente para desenvolvimento remoto via SSH.",
                "strengths": ["Fresco e silencioso", "Excelente para SSH e web dev"]
            })
        return result

    # 6. Intel 11ª Geração (i7-11800H, i7-11850H, i7-1165G7, i5-11400H)
    if any(x in full_text for x in ["11800h", "11850h", "11400h", "1165g", "1135g", "1185g", "1155g", "1145g"]):
        if any(x in full_text for x in ["11800h", "11850h"]):
            result.update({
                "model_name": "Intel Core i7-11800H / 11850H",
                "family": "Intel Core i7",
                "generation": "11ª Geração Tiger Lake-H (10nm SuperFin)",
                "release_year": 2021,
                "cores_threads": "8 Núcleos / 16 Threads",
                "architecture_nm": "10nm SuperFin",
                "passmark_score": 20800,
                "compute_tier": 83,
                "single_core_tier": 84,
                "equivalents": {
                    "intel": "Intel Core i5-12500H",
                    "amd": "AMD Ryzen 7 5800H",
                    "apple": "Apple M1 Pro (8-Core)",
                    "snapdragon": "Snapdragon X Plus"
                },
                "engineer_summary": "Primeiro grande salto da Intel para 10nm em portáteis de alta performance. 8 núcleos potentes com instruções completas AVX-512 (ótimo para computação numérica e IA em CPU).",
                "strengths": ["Suporte a instruções AVX-512 nativas", "8 Núcleos completos", "PCIe 4.0 x16"]
            })
        elif "11400h" in full_text:
            result.update({
                "model_name": "Intel Core i5-11400H (6C/12T)",
                "family": "Intel Core i5",
                "generation": "11ª Geração Tiger Lake-H (10nm)",
                "release_year": 2021,
                "cores_threads": "6 Núcleos / 12 Threads",
                "architecture_nm": "10nm SuperFin",
                "passmark_score": 15900,
                "compute_tier": 74,
                "single_core_tier": 80,
                "equivalents": {
                    "intel": "Intel Core i7-10750H (supera a 10ª gen)",
                    "amd": "AMD Ryzen 5 5600H",
                    "apple": "Apple M1",
                    "snapdragon": "Snapdragon 8cx Gen 3"
                },
                "engineer_summary": "6 núcleos sólidos com bom desempenho mono-thread e AVX-512.",
                "strengths": ["6 Núcleos", "Instruções AVX-512"]
            })
        else:
            result.update({
                "model_name": "Intel Core i7/i5 11ª Geração (Série G7)",
                "family": "Intel Core",
                "generation": "11ª Geração Tiger Lake (10nm)",
                "release_year": 2020,
                "cores_threads": "4 Núcleos / 8 Threads",
                "architecture_nm": "10nm",
                "passmark_score": 10500,
                "compute_tier": 58,
                "single_core_tier": 78,
                "equivalents": {
                    "intel": "Intel Core i7-1065G7 / Core i3-1215U",
                    "amd": "AMD Ryzen 5 4500U / Ryzen 3 5300U",
                    "apple": "Apple A14 / M1 (M1 é significativamente mais rápido em multi)",
                    "snapdragon": "Snapdragon 8cx Gen 2"
                },
                "engineer_summary": "Quad-core de baixo consumo com gráfica Intel Iris Xe. Bom para escritório e dev leve, mas limitado para compilação pesada por ter apenas 4 núcleos.",
                "strengths": ["Gráfica Iris Xe 96EU", "AVX-512", "Baixo consumo"]
            })
        return result

    # 7. Apple Silicon (M1, M2, M3, Pro, Max)
    is_apple_brand = "apple" in full_text or "macbook" in full_text or "macos" in full_text
    has_apple_chip = bool(re.search(r'\bm[123](?:\s*(?:pro|max))?\b', full_text))
    if is_apple_brand and has_apple_chip:
        if any(x in full_text for x in ["m3 pro", "m3 max", "m2 pro", "m2 max", "m1 pro", "m1 max"]):
            result.update({
                "model_name": "Apple Silicon Pro / Max",
                "family": "Apple Silicon",
                "generation": "ARM SoC Apple Silicon Pro",
                "release_year": 2022,
                "cores_threads": "10 a 14 Núcleos ARM",
                "architecture_nm": "5nm / 3nm TSMC",
                "passmark_score": 23000,
                "compute_tier": 88,
                "single_core_tier": 93,
                "equivalents": {
                    "intel": "Intel Core i7-13700H / Core Ultra 7",
                    "amd": "AMD Ryzen 7 7840HS",
                    "apple": "Nativo Apple Silicon",
                    "snapdragon": "Qualcomm Snapdragon X Elite"
                },
                "engineer_summary": "Excelente eficiência energética e autonomia de 15h+. Nota: roda macOS nativo; não suporta Linux x86_64 nem dual boot Debian oficial.",
                "strengths": ["Autonomia incrível", "Memória unificada ultrarrápida"]
            })
        else:
            result.update({
                "model_name": "Apple M1 / M2 / M3",
                "family": "Apple Silicon",
                "generation": "ARM SoC Apple Silicon",
                "release_year": 2021,
                "cores_threads": "8 Núcleos (4P + 4E) / 8 Threads",
                "architecture_nm": "5nm TSMC",
                "passmark_score": 14900,
                "compute_tier": 72,
                "single_core_tier": 89,
                "equivalents": {
                    "intel": "Intel Core i5-1240P / i7-1165G7",
                    "amd": "AMD Ryzen 5 5600U / Ryzen 7 5700U",
                    "apple": "Nativo Apple Silicon",
                    "snapdragon": "Snapdragon X Plus"
                },
                "engineer_summary": "Muito rápido e eficiente em macOS. Se precisas de correr Debian/Linux nativo x86 para ferramentas industriais ou Docker x86, requer emulação Rosetta.",
                "strengths": ["Fresco sem ventoinhas audíveis", "Excelente ecrã e teclado"]
            })
        return result

    # 8. Snapdragon X Elite / Plus
    if "snapdragon" in full_text:
        result.update({
            "model_name": "Qualcomm Snapdragon X Elite / Plus",
            "family": "Snapdragon ARM",
            "generation": "Oryon ARM64 (4nm TSMC)",
            "release_year": 2024,
            "cores_threads": "10 a 12 Núcleos ARM64",
            "architecture_nm": "4nm TSMC",
            "passmark_score": 23500,
            "compute_tier": 86,
            "single_core_tier": 88,
            "equivalents": {
                "intel": "Intel Core Ultra 7 155H",
                "amd": "AMD Ryzen 7 7840HS",
                "apple": "Apple M2 / M3",
                "snapdragon": "Snapdragon X Series"
            },
            "engineer_summary": "Arquitetura ARM64 para Windows Copilot+ PC. Excelente bateria, mas requer cuidado se precisas de compilar binários x86 ou usar drivers Linux legados.",
            "strengths": ["NPU de 45 TOPS", "Bateria de longa duração"]
        })
        return result

    # 9. Processadores Antigos / "Potato Alert" (Intel 6ª/7ª/8ª/9ª/10ª Geração e Xeons antigos)
    if any(x in full_text for x in ["xeon", "7820hq", "6700hq", "7700hq", "8850h", "9750h", "10750h", "8550u", "8650u", "8350u", "8250u", "6300u", "5300u", "4300u"]):
        is_quad = any(x in full_text for x in ["xeon", "7820", "6700", "7700", "8550", "8650", "8350", "8250", "6300"])
        score = 5200 if is_quad else 11500
        tier = 32 if is_quad else 50
        result.update({
            "model_name": cpu_str or "Intel Core Antigo (Pré-2020)",
            "family": "Intel Legado (14nm)",
            "generation": "Skylake / Kaby Lake / Comet Lake (14nm)",
            "release_year": 2017 if is_quad else 2020,
            "cores_threads": "4 Núcleos / 8 Threads" if is_quad else "6 Núcleos / 12 Threads",
            "architecture_nm": "14nm (Consumo e calor mais altos)",
            "passmark_score": score,
            "compute_tier": tier,
            "single_core_tier": 45,
            "equivalents": {
                "intel": "Intel Processor N100 / Core i3 moderno (qualquer CPU atual de 50€ supera este)",
                "amd": "AMD Ryzen 3 3200U / Ryzen 5 2500U",
                "apple": "Apple A13 Bionic (iPhone 11)",
                "snapdragon": "Snapdragon 850 (Legado)"
            },
            "engineer_summary": "⚠️ Arquitetura antiga de 14nm. Embora alguns modelos tenham 32GB ou 64GB de RAM, o processador é limitado a 4 ou 6 núcleos antigos, esquenta facilmente e tem um terço da velocidade de um Ryzen 5800H ou i7-13620H.",
            "strengths": ["Preço de sucata", "Suficiente apenas para servidor SSH básico sem carga pesada"]
        })
        return result

    # 10. AMD Ryzen 5 modernos (5600H, 7535HS, 5500U)
    if any(x in full_text for x in ["5600h", "7535hs", "5500u", "5600", "7535", "5675u"]):
        result.update({
            "model_name": "AMD Ryzen 5 (Série 5000/7000)",
            "family": "AMD Ryzen 5",
            "generation": "Zen 3 / Zen 3+ (7nm/6nm)",
            "release_year": 2022,
            "cores_threads": "6 Núcleos / 12 Threads",
            "architecture_nm": "7nm / 6nm",
            "passmark_score": 17200,
            "compute_tier": 77,
            "single_core_tier": 82,
            "equivalents": {
                "intel": "Intel Core i5-11400H / Core i5-1235U",
                "amd": "AMD Ryzen 7 4800H",
                "apple": "Apple M1",
                "snapdragon": "Snapdragon X Plus"
            },
            "engineer_summary": "Processador de 6 núcleos e 12 threads moderno e muito fiável. Muito bom para desenvolvimento diário, Docker e compilação sem aquecer.",
            "strengths": ["6 Núcleos eficientes", "Excelente estabilidade térmica"]
        })
        return result

    return result


def analyze_gpu(gpu_str: Optional[str], title_str: str = "", text_str: str = "", ram_gb: int = 16) -> Dict[str, Any]:
    """
    Comprehensive, deterministic GPU & VRAM comparator and analyzer.
    Answers:
    - How much VRAM does it have? (Shared system RAM vs Dedicated GDDR6)
    - What NVIDIA / AMD GPU is it equivalent to?
    - How does it handle Local AI models (Ollama, PyTorch, LLMs), Gaming, and Engineering workloads?
    """
    full_text = f"{title_str} {gpu_str or ''} {text_str}".lower()
    safe_ram = int(ram_gb) if (ram_gb is not None and isinstance(ram_gb, (int, float)) and ram_gb > 0) else 16

    # Default fallback
    result = {
        "model_name": gpu_str or "Gráfica Integrada",
        "is_dedicated": False,
        "vram_gb": max(safe_ram // 2, 2),
        "vram_type": "Memória Partilhada (Shared RAM)",
        "vram_description": f"Até {max(safe_ram // 2, 2)} GB dinamicamente alocados da memória RAM do sistema. Não tem chips de memória de vídeo dedicada (GDDR).",
        "architecture": "Integrada no Processador",
        "tgp_watts": 15,
        "benchmark_tier": 25,
        "equivalents": {
            "nvidia": "NVIDIA GeForce GT 1030 / MX350",
            "amd": "AMD Radeon Vega integrada"
        },
        "ai_workload": {
            "rating": "Apenas CPU (Lento)",
            "color": "amber",
            "text": "Não tem aceleração CUDA dedicada. Modelos de IA (Ollama / PyTorch) correm via CPU e RAM do sistema (~2-5 tokens/segundo)."
        },
        "gaming_workload": {
            "rating": "Básico / 720p",
            "color": "zinc",
            "text": "Adequado para jogos 2D, e-sports leves (LoL, CS2 em baixa resolução) e aceleração de vídeo."
        },
        "engineering_workload": {
            "rating": "Perfeito",
            "color": "emerald",
            "text": "Consome zero energia extra. Ideal para múltiplos ecrãs, terminal, SSH e ambientes de desenvolvimento web."
        },
        "engineer_summary": "Gráfica integrada simples para trabalho geral. Mantém a máquina fresca e com bateria de longa duração."
    }

    # 1. NVIDIA RTX 4060 (8GB)
    if "4060" in full_text:
        result.update({
            "model_name": "NVIDIA GeForce RTX 4060 Laptop (8GB)",
            "is_dedicated": True,
            "vram_gb": 8,
            "vram_type": "8 GB GDDR6 Dedicada (128-bit bus)",
            "vram_description": "8 GB de memória de vídeo GDDR6 ultra-rápida dedicada com ~256 GB/s de largura de banda.",
            "architecture": "NVIDIA Ada Lovelace (4nm TSMC)",
            "tgp_watts": 115,
            "benchmark_tier": 95,
            "equivalents": {
                "nvidia": "NVIDIA RTX 3070 Mobile / Desktop RTX 3060 12GB (em velocidade de computação)",
                "amd": "AMD Radeon RX 7600M XT"
            },
            "ai_workload": {
                "rating": "Excelente (Top Sweet-Spot)",
                "color": "emerald",
                "text": "⭐ Ponto ideal para IA local: os 8 GB de VRAM permitem carregar Llama-3 8B, Qwen 2.5 7B ou Mistral 7B inteiros na GPU com quantização 4-bit (Q4_K_M ocupa ~4.8 GB), deixando 3 GB livres para contexto de 8k tokens a ~35-45 tok/s."
            },
            "gaming_workload": {
                "rating": "1080p / 1440p Ultra",
                "color": "purple",
                "text": "Corre qualquer jogo moderno no máximo com DLSS 3 e Frame Generation."
            },
            "engineering_workload": {
                "rating": "Topo de Gama",
                "color": "blue",
                "text": "CUDA 12.x nativo, Tensor Cores de 4ª geração com precisão FP8 para treino e inferência rápida de PyTorch."
            },
            "engineer_summary": "A melhor placa custo/benefício atual para quem quer correr modelos de IA locais no portátil com folga de VRAM."
        })
        return result

    # 2. NVIDIA RTX 4050 (6GB)
    if "4050" in full_text:
        result.update({
            "model_name": "NVIDIA GeForce RTX 4050 Laptop (6GB)",
            "is_dedicated": True,
            "vram_gb": 6,
            "vram_type": "6 GB GDDR6 Dedicada (96-bit bus)",
            "vram_description": "6 GB de memória GDDR6 dedicada com ~192 GB/s de largura de banda e suporte a compressão de memória Ada.",
            "architecture": "NVIDIA Ada Lovelace (4nm TSMC)",
            "tgp_watts": 75,
            "benchmark_tier": 86,
            "equivalents": {
                "nvidia": "NVIDIA RTX 3060 Laptop (empata em rasterização, ganha em IA graças aos Tensor Cores FP8 e DLSS 3)",
                "amd": "AMD Radeon RX 7600M"
            },
            "ai_workload": {
                "rating": "Muito Bom (7B Models)",
                "color": "emerald",
                "text": "✅ Corre modelos locais de 7B e 8B (Llama 3 8B Q4_K_M ocupa ~4.5 GB) 100% carregados na VRAM com aceleração CUDA nativa (~25 a 35 tokens/s via Ollama)."
            },
            "gaming_workload": {
                "rating": "1080p Alto / Ultra",
                "color": "purple",
                "text": "Excelente para 1080p moderno com tecnologia DLSS 3 Frame Generation ativada."
            },
            "engineering_workload": {
                "rating": "Excelente",
                "color": "blue",
                "text": "Arquitetura Ada de 4nm consome metade da energia da série 3000 para a mesma performance CUDA."
            },
            "engineer_summary": "Excelente equilíbrio entre preço e inteligência artificial. Os 6GB de VRAM GDDR6 chegam perfeitamente para LLMs locais de 7B/8B e código acelerado por GPU."
        })
        return result

    # 3. NVIDIA RTX 3060 (6GB)
    if "3060" in full_text:
        result.update({
            "model_name": "NVIDIA GeForce RTX 3060 Laptop (6GB)",
            "is_dedicated": True,
            "vram_gb": 6,
            "vram_type": "6 GB GDDR6 Dedicada (192-bit bus largo)",
            "vram_description": "6 GB GDDR6 com barramento largo de 192-bit (~336 GB/s de largura de banda direta).",
            "architecture": "NVIDIA Ampere (8nm Samsung)",
            "tgp_watts": 130,
            "benchmark_tier": 87,
            "equivalents": {
                "nvidia": "NVIDIA RTX 4050 Laptop / RTX 2070 Super Mobile",
                "amd": "AMD Radeon RX 6600M"
            },
            "ai_workload": {
                "rating": "Muito Bom (Largura de Banda Alta)",
                "color": "emerald",
                "text": "✅ A largura de banda de 336 GB/s faz maravilhas em PyTorch e modelos quantizados de 7B/8B. Suporte completo a drivers proprietários CUDA no Linux."
            },
            "gaming_workload": {
                "rating": "1080p Ultra",
                "color": "purple",
                "text": "Desempenho clássico e robusto para qualquer jogo em 1080p e renderização Blender."
            },
            "engineering_workload": {
                "rating": "Excelente",
                "color": "blue",
                "text": "3840 núcleos CUDA de alta taxa de preenchimento. Mais quente que a série 40, mas com grande poder de cálculo."
            },
            "engineer_summary": "Placa muito sólida com barramento de memória largo (192-bit), ideal para computação paralela pura e modelos de 7B."
        })
        return result

    # 4. NVIDIA RTX 3050 Ti (4GB)
    if "3050 ti" in full_text or "3050ti" in full_text:
        result.update({
            "model_name": "NVIDIA GeForce RTX 3050 Ti Laptop (4GB)",
            "is_dedicated": True,
            "vram_gb": 4,
            "vram_type": "4 GB GDDR6 Dedicada (128-bit bus)",
            "vram_description": "4 GB de memória GDDR6 dedicada com ~192 GB/s de largura de banda.",
            "architecture": "NVIDIA Ampere (8nm Samsung)",
            "tgp_watts": 60,
            "benchmark_tier": 70,
            "equivalents": {
                "nvidia": "NVIDIA RTX 2060 Max-Q / GTX 1660 Ti Mobile (com núcleos Tensor)",
                "amd": "AMD Radeon RX 6500M"
            },
            "ai_workload": {
                "rating": "Moderado (Modelos 3B/4B)",
                "color": "blue",
                "text": "⚠️ 4 GB de VRAM é suficiente para correr modelos leves (Phi-3 3.8B, Llama-3.2 3B, Gemma 2B) 100% em GPU. Modelos de 7B/8B requerem partilhar camadas com a RAM do sistema (offloading)."
            },
            "gaming_workload": {
                "rating": "1080p Médio / Alto",
                "color": "purple",
                "text": "Corre a maioria dos jogos a 1080p usando DLSS 2 para compensar os 4GB de VRAM."
            },
            "engineering_workload": {
                "rating": "Bom",
                "color": "blue",
                "text": "2560 núcleos CUDA para aceleração de filtros, renderização e processamento paralelo."
            },
            "engineer_summary": "GPU dedicada económica. Ótima para trabalho e código com aceleração CUDA, mas com limite de 4GB que restringe LLMs gigantes a rodar parte na RAM."
        })
        return result

    # 5. NVIDIA RTX 3050 (4GB / 6GB)
    if "3050" in full_text:
        has_6gb = "6gb" in full_text or "6 gb" in full_text
        v_size = 6 if has_6gb else 4
        result.update({
            "model_name": f"NVIDIA GeForce RTX 3050 Laptop ({v_size}GB)",
            "is_dedicated": True,
            "vram_gb": v_size,
            "vram_type": f"{v_size} GB GDDR6 Dedicada",
            "vram_description": f"{v_size} GB GDDR6 dedicada para processamento gráfico e aceleração de cálculo.",
            "architecture": "NVIDIA Ampere (8nm Samsung)",
            "tgp_watts": 60,
            "benchmark_tier": 68 if has_6gb else 64,
            "equivalents": {
                "nvidia": "NVIDIA GTX 1660 Ti / GTX 1650 Super (com núcleos Tensor para DLSS e IA)",
                "amd": "AMD Radeon RX 6500M"
            },
            "ai_workload": {
                "rating": "Bom para 3B/7B" if has_6gb else "Moderado (3B)",
                "color": "emerald" if has_6gb else "blue",
                "text": f"{'✅ 6 GB acomodam modelos de 7B/8B quantizados.' if has_6gb else '⚠️ 4 GB acomodam modelos até 3B (Phi-3, Gemma-2B). Modelos de 7B requerem offload para RAM.'}"
            },
            "gaming_workload": {
                "rating": "1080p Médio",
                "color": "purple",
                "text": "Jogos modernos a 1080p com suporte a DLSS."
            },
            "engineering_workload": {
                "rating": "Bom",
                "color": "blue",
                "text": "Aceleração CUDA estável para bibliotecas de machine learning e simulação."
            },
            "engineer_summary": "Placa de entrada com suporte a CUDA e Tensor Cores. Uma escolha sólida para quem quer GPU dedicada sem estourar o orçamento."
        })
        return result

    # 6. AMD Radeon 780M / 680M (Integradas topo de gama RDNA2/RDNA3)
    if any(x in full_text for x in ["780m", "680m", "radeon 780", "radeon 680"]):
        is_780 = "780" in full_text
        result.update({
            "model_name": "AMD Radeon 780M (RDNA 3)" if is_780 else "AMD Radeon 680M (RDNA 2)",
            "is_dedicated": False,
            "vram_gb": max(ram_gb // 2, 4),
            "vram_type": "Memória Partilhada do Sistema (Shared RAM)",
            "vram_description": f"Usa até {max(ram_gb // 2, 4)} GB da RAM do sistema. Se o portátil tiver DDR5 rápida a 5600MHz, atinge larguras de banda impressionantes para uma integrada.",
            "architecture": "AMD RDNA 3 (4nm)" if is_780 else "AMD RDNA 2 (6nm)",
            "tgp_watts": 25,
            "benchmark_tier": 55 if is_780 else 48,
            "equivalents": {
                "nvidia": "NVIDIA GTX 1650 Ti / GTX 1650 Max-Q (a gráfica integrada mais rápida do mercado)",
                "amd": "AMD Radeon RX 560X Dedicada"
            },
            "ai_workload": {
                "rating": "Suporte ROCm / RAM Aberta",
                "color": "blue",
                "text": "Por usar a memória RAM do sistema, pode alocar até 16 GB de contexto se o portátil tiver 32 GB RAM, embora com velocidade de transferência menor que uma RTX com GDDR6."
            },
            "gaming_workload": {
                "rating": "1080p Médio (Muito Bom para iGPU)",
                "color": "purple",
                "text": "Corre GTA V, Witcher 3, Cyberpunk a 1080p 40-50fps sem placa gráfica dedicada!"
            },
            "engineering_workload": {
                "rating": "Excelente para Eficiência",
                "color": "emerald",
                "text": "Consumo de bateria mínimo com potência gráfica comparável a uma placa dedicada de entrada de há poucos anos."
            },
            "engineer_summary": "A rainha das gráficas integradas. Permite jogar e renderizar com consumo mínimo de bateria e sem ventoinhas a fazer barulho de turbina."
        })
        return result

    # 7. Intel Arc Graphics (no Core Ultra)
    if any(x in full_text for x in ["intel arc", "arc graphics", "core ultra", "ultra 7", "ultra 5", "155h", "125h"]):
        result.update({
            "model_name": "Intel Arc Graphics (8 Xe-Cores)",
            "is_dedicated": False,
            "vram_gb": max(ram_gb // 2, 4),
            "vram_type": "Memória Partilhada do Sistema (Shared RAM)",
            "vram_description": f"Aloca dinamicamente até {max(ram_gb // 2, 4)} GB da memória RAM do sistema.",
            "architecture": "Intel Xe-LPG (Meteor Lake)",
            "tgp_watts": 28,
            "benchmark_tier": 50,
            "equivalents": {
                "nvidia": "NVIDIA GTX 1650 Max-Q / GTX 1050 Ti",
                "amd": "AMD Radeon 780M / 680M"
            },
            "ai_workload": {
                "rating": "Intel OpenVINO / DirectML",
                "color": "blue",
                "text": "Otimizado para o ecossistema Intel OpenVINO e tarefas de visão computacional aceleradas."
            },
            "gaming_workload": {
                "rating": "1080p Médio",
                "color": "purple",
                "text": "Suporta Intel XeSS (upscaling de IA) para 1080p fluido."
            },
            "engineering_workload": {
                "rating": "Excelente",
                "color": "emerald",
                "text": "Codificação e descodificação nativa AV1 por hardware, duplo ecrã 4K/8K."
            },
            "engineer_summary": "Grande evolução da Intel em gráficas integradas. O dobro da velocidade da antiga Iris Xe com suporte moderno a AV1."
        })
        return result

    # 8. Intel Iris Xe Graphics
    if "iris xe" in full_text or "iris" in full_text:
        result.update({
            "model_name": "Intel Iris Xe Graphics (80/96 EUs)",
            "is_dedicated": False,
            "vram_gb": max(ram_gb // 2, 2),
            "vram_type": "Memória Partilhada (Shared RAM)",
            "vram_description": f"Aloca dinamicamente até {max(ram_gb // 2, 2)} GB da memória RAM principal.",
            "architecture": "Intel Gen 12 Xe-LP (10nm)",
            "tgp_watts": 15,
            "benchmark_tier": 32,
            "equivalents": {
                "nvidia": "NVIDIA GeForce MX350 / GT 1030 Desktop",
                "amd": "AMD Radeon Vega 8"
            },
            "ai_workload": {
                "rating": "Apenas CPU/OpenVINO básico",
                "color": "amber",
                "text": "Sem CUDA. Modelos LLM grandes correm exclusivamente via CPU na memória RAM."
            },
            "gaming_workload": {
                "rating": "720p / 1080p Baixo",
                "color": "zinc",
                "text": "Jogos leves como CS:GO, LoL, Rocket League e emuladores retro."
            },
            "engineering_workload": {
                "rating": "Excelente para Trabalho Puro",
                "color": "emerald",
                "text": "Consumo de bateria mínimo, suporte QuickSync para vídeo e estabilidade impecável em Linux."
            },
            "engineer_summary": "Gráfica integrada de escritório moderna. Excelente para programar, trabalhar em múltiplos monitores e poupar bateria, mas não indicada para IA pesada nem gaming 3D."
        })
        return result

    # 9. NVIDIA GTX 1650 / 1660 Ti
    if any(x in full_text for x in ["1650", "1660", "gtx 1060"]):
        is_1660 = "1660" in full_text or "1060" in full_text
        result.update({
            "model_name": "NVIDIA GeForce GTX 1660 Ti (6GB)" if is_1660 else "NVIDIA GeForce GTX 1650 (4GB)",
            "is_dedicated": True,
            "vram_gb": 6 if is_1660 else 4,
            "vram_type": f"{6 if is_1660 else 4} GB GDDR5/GDDR6 Dedicada",
            "vram_description": f"{6 if is_1660 else 4} GB de memória dedicada dedicada.",
            "architecture": "NVIDIA Turing / Pascal (12nm/16nm)",
            "tgp_watts": 65,
            "benchmark_tier": 62 if is_1660 else 48,
            "equivalents": {
                "nvidia": "NVIDIA RTX 3050 (sem núcleos Tensor/RT) / GTX 1060",
                "amd": "AMD Radeon RX 5500M / RX 580"
            },
            "ai_workload": {
                "rating": "Básico (Sem Tensor Cores)",
                "color": "amber",
                "text": "Tem núcleos CUDA normais para acelerar código, mas falta-lhe Tensor Cores e precisão FP8/FP16 rápida de arquiteturas modernas."
            },
            "gaming_workload": {
                "rating": "1080p Médio",
                "color": "purple",
                "text": "Boa para jogos competitivos em 1080p, mas sem DLSS."
            },
            "engineering_workload": {
                "rating": "Bom",
                "color": "blue",
                "text": "Suporte a drivers CUDA no Linux para renderização e cálculo numérico."
            },
            "engineer_summary": "Placa dedicada da geração anterior. Funciona bem para tarefas gráficas, mas hoje em dia a série RTX 3000/4000 compensa muito mais para IA e longevidade."
        })
        return result

    # 10. NVIDIA Quadro Workstation GPUs (M1200, M2000M, P1000, T1000)
    if "quadro" in full_text:
        result.update({
            "model_name": "NVIDIA Quadro Mobile (Workstation)",
            "is_dedicated": True,
            "vram_gb": 4,
            "vram_type": "4 GB GDDR5 Dedicada",
            "vram_description": "4 GB de memória GDDR5 dedicada para estações de trabalho móveis antigas (CAD/3D legado).",
            "architecture": "NVIDIA Maxwell / Pascal",
            "tgp_watts": 55,
            "benchmark_tier": 35,
            "equivalents": {
                "nvidia": "NVIDIA GeForce GTX 960M / GTX 950M (equivalente a gráfica de 2015)",
                "amd": "AMD Radeon Pro 555"
            },
            "ai_workload": {
                "rating": "Muito Lento (CUDA Antigo)",
                "color": "amber",
                "text": "CUDA compute capability antiga (5.2/6.1). Não suporta FP16 rápido nem Tensor Cores. Modelos modernos de IA correm com muita lentidão."
            },
            "gaming_workload": {
                "rating": "720p / 1080p Baixo",
                "color": "zinc",
                "text": "Desempenho equivalente a uma GeForce antiga de 2015."
            },
            "engineering_workload": {
                "rating": "Estável para CAD Antigo",
                "color": "blue",
                "text": "Drivers certificados para AutoCAD antigo e Solidworks legado."
            },
            "engineer_summary": "Placa de estação de trabalho antiga (2015-2017). Para código geral e terminal serve, mas está completamente ultrapassada para IA moderna e gráficos atuais."
        })
        return result

    # 11. Apple Silicon Integrated GPU (M1, M2, M3)
    is_apple_brand_gpu = "apple" in full_text or "macbook" in full_text or "macos" in full_text
    has_apple_chip_gpu = bool(re.search(r'\bm[123](?:\s*(?:pro|max))?\b', full_text))
    if is_apple_brand_gpu and has_apple_chip_gpu:
        result.update({
            "model_name": "Apple Silicon Unified GPU",
            "is_dedicated": False,
            "vram_gb": ram_gb,
            "vram_type": f"Memória Unificada Apple ({ram_gb} GB)",
            "vram_description": f"Memória Unificada de altíssima largura de banda (~100-200 GB/s) partilhada diretamente entre CPU e GPU. O sistema pode usar praticamente todos os {ram_gb} GB para carregar modelos de IA via MLX / Metal.",
            "architecture": "Apple Metal Architecture (3nm/5nm)",
            "tgp_watts": 20,
            "benchmark_tier": 65,
            "equivalents": {
                "nvidia": "NVIDIA GTX 1650 Ti / RTX 3050 (em aceleração de modelos via framework Apple MLX)",
                "amd": "AMD Radeon 780M"
            },
            "ai_workload": {
                "rating": "Excelente via Apple MLX",
                "color": "emerald",
                "text": "Executa modelos de IA locais muito eficientemente usando o framework Apple MLX e aceleração Metal nativa em macOS."
            },
            "gaming_workload": {
                "rating": "Médio (Depende de suporte macOS)",
                "color": "zinc",
                "text": "Excelente hardware, mas biblioteca de jogos no macOS é reduzida."
            },
            "engineering_workload": {
                "rating": "Excelente para macOS",
                "color": "emerald",
                "text": "Terminal UNIX nativo, compilação silenciosa sem aquecimento e bateria fabulosa."
            },
            "engineer_summary": "Gráfica unificada excelente para quem trabalha no ecossistema Mac. Para Linux nativo (Debian), não é recomendável."
        })
        return result

    # 11. Intel UHD Graphics (Legado / 620 / 630 / etc.)
    if any(x in full_text for x in ["uhd", "hd graphics", "620", "630", "xeon", "7820hq", "6700hq", "8550u", "8650u", "8250u", "6300u"]):
        result.update({
            "model_name": "Intel UHD / HD Graphics (Legado)",
            "is_dedicated": False,
            "vram_gb": 2,
            "vram_type": "Memória Partilhada Básica (até 2 GB)",
            "vram_description": "Aloca até 2 GB da memória RAM do sistema apenas para interface visual e ecrã. Não tem aceleração de computação moderna.",
            "architecture": "Intel Gen 9/9.5 (14nm)",
            "tgp_watts": 15,
            "benchmark_tier": 15,
            "equivalents": {
                "nvidia": "NVIDIA GeForce 920M / GT 710 (Apenas ecrã e 2D)",
                "amd": "AMD Radeon R5 integrada"
            },
            "ai_workload": {
                "rating": "Sem suporte GPU (Apenas CPU)",
                "color": "amber",
                "text": "Não tem aceleração para IA. Qualquer execução de Ollama roda 100% no CPU em modo lento."
            },
            "gaming_workload": {
                "rating": "Muito Fraco",
                "color": "zinc",
                "text": "Apenas jogos 2D simples e tarefas de desktop."
            },
            "engineering_workload": {
                "rating": "Apenas Terminal e Código",
                "color": "blue",
                "text": "Suficiente para terminal, Vim, VS Code básico e SSH."
            },
            "engineer_summary": "Gráfica básica antiga. Serve perfeitamente para terminal e SSH, mas zero capacidade de aceleração para IA moderna ou 3D."
        })
        return result

    return result


def get_hardware_dossier(laptop: Dict[str, Any]) -> Dict[str, Any]:
    """
    Combines CPU, GPU, RAM and Storage into a structured hardware evaluation dossier.
    """
    cpu_analysis = analyze_cpu(
        cpu_str=laptop.get("cpu"),
        title_str=laptop.get("title", ""),
        text_str=laptop.get("description", "")
    )

    gpu_analysis = analyze_gpu(
        gpu_str=laptop.get("gpu"),
        title_str=laptop.get("title", ""),
        text_str=laptop.get("description", ""),
        ram_gb=laptop.get("ram_gb") or 16
    )

    ram_gb = laptop.get("ram_gb") or 8
    ram_type = laptop.get("ram_type") or ("DDR5" if "ddr5" in str(laptop.get("title", "")).lower() else "DDR4")
    
    storage_gb = laptop.get("storage_gb") or 512
    storage_type = laptop.get("storage_type") or "SSD"

    # Synthesis verdict for an engineer
    overall_hardware_score = round((cpu_analysis["compute_tier"] * 0.5 + gpu_analysis["benchmark_tier"] * 0.3 + min(ram_gb, 32) * 0.6), 1)
    power = calculate_power_specs(laptop.get("cpu"), laptop.get("gpu"), laptop.get("brand"))
    price_val = float(laptop.get("price") or 500)
    value_score = round((overall_hardware_score / max(price_val, 100.0)) * 100, 2)

    return {
        "id": laptop.get("id"),
        "title": laptop.get("title"),
        "price": laptop.get("price"),
        "spec_score": laptop.get("spec_score") or overall_hardware_score,
        "value_score": value_score,
        "deal_score": laptop.get("deal_score") or overall_hardware_score,
        "hardware_index": overall_hardware_score,
        "monthly_cost_eur": power.get("monthly_cost_eur"),
        "power_idle_watts": power.get("power_idle_watts"),
        "power_peak_watts": power.get("power_peak_watts"),
        "cpu": cpu_analysis,
        "gpu": gpu_analysis,
        "ram": {
            "capacity_gb": ram_gb,
            "type": ram_type,
            "display": f"{ram_gb} GB {ram_type}",
            "vm_capacity": "Host Perfeito (4+ VMs)" if ram_gb >= 32 else ("Pronto para 2 VMs" if ram_gb >= 16 else "Básico (1 VM leve)")
        },
        "storage": {
            "capacity_gb": storage_gb,
            "type": storage_type,
            "display": f"{storage_gb / 1000:.0f} TB {storage_type}" if storage_gb >= 1000 else f"{storage_gb} GB {storage_type}"
        }
    }


class HardwareComparator:
    """Class wrapper for hardware evaluation methods."""
    def __init__(self):
        pass

    def get_laptop_hardware_dossier(self, laptop: Dict[str, Any]) -> Dict[str, Any]:
        return get_hardware_dossier(laptop)

    def analyze_cpu(self, cpu_str: Optional[str] = None, title_str: str = "", text_str: str = "") -> Dict[str, Any]:
        return analyze_cpu(cpu_str, title_str, text_str)

    def analyze_gpu(self, gpu_str: Optional[str] = None, title_str: str = "", text_str: str = "", ram_gb: int = 16) -> Dict[str, Any]:
        return analyze_gpu(gpu_str, title_str, text_str, ram_gb)

