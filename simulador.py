#!/usr/bin/env python3
"""Simulador de escalonamento de processos (SRTF e RR).

Uso:
    python simulador.py < entrada.json > resultado.json

Organização:
    1. Leitura e validação  -> ler_entrada(), validar()
    2. Políticas            -> simular_srtf(), simular_rr()
    3. Linha do tempo       -> LinhaDoTempo (registra e une intervalos)
    4. Métricas             -> calcular_metricas()
"""
import json
import sys

ALGORITMOS = ("SRTF", "RR")


class EntradaInvalida(Exception):
    pass


# --------------------------------------------------------------------------
# 1. Leitura e validação
# --------------------------------------------------------------------------
def eh_inteiro(v):
    # bool é subclasse de int em Python; True/False não podem passar como número
    return isinstance(v, int) and not isinstance(v, bool)


def ler_entrada(texto):
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        raise EntradaInvalida("A entrada não é um JSON válido.")


def validar(dados):
    if not isinstance(dados, dict):
        raise EntradaInvalida("A entrada deve ser um objeto JSON.")

    algoritmo = dados.get("algoritmo")
    if not isinstance(algoritmo, str) or not algoritmo:
        raise EntradaInvalida("O campo 'algoritmo' é obrigatório e deve ser uma string.")
    if algoritmo not in ALGORITMOS:
        raise EntradaInvalida(f"Algoritmo não implementado: {algoritmo}.")

    config = dados.get("configuracao")
    if not isinstance(config, dict):
        raise EntradaInvalida("O campo 'configuracao' é obrigatório e deve ser um objeto.")

    quantum = None
    if algoritmo == "RR":
        quantum = config.get("quantum")
        if not eh_inteiro(quantum) or quantum <= 0:
            raise EntradaInvalida("Para RR, 'quantum' deve ser um inteiro positivo.")
    # Parâmetros de outros algoritmos são ignorados.

    processos = dados.get("processos")
    if not isinstance(processos, list) or not processos:
        raise EntradaInvalida("O campo 'processos' deve ser uma lista não vazia.")

    vistos = set()
    lista = []
    for p in processos:
        if not isinstance(p, dict):
            raise EntradaInvalida("Cada processo deve ser um objeto.")
        pid = p.get("id")
        if not isinstance(pid, str) or not pid:
            raise EntradaInvalida("O ID do processo deve ser uma string não vazia.")
        if pid == "OCIOSO":
            raise EntradaInvalida("O ID 'OCIOSO' é reservado.")
        if pid in vistos:
            raise EntradaInvalida(f"ID duplicado: {pid}.")
        vistos.add(pid)
        chegada = p.get("chegada")
        if not eh_inteiro(chegada) or chegada < 0:
            raise EntradaInvalida("O instante de chegada deve ser um inteiro maior ou igual a zero.")
        cpu = p.get("cpu")
        if not eh_inteiro(cpu) or cpu <= 0:
            raise EntradaInvalida("O tempo de CPU deve ser um inteiro positivo.")
        # 'peso' e outros campos são ignorados (só o CFS usaria).
        lista.append({"id": pid, "chegada": chegada, "cpu": cpu})

    # A ordem do arquivo não importa: ordenar por chegada e, depois, por ID.
    lista.sort(key=lambda p: (p["chegada"], p["id"]))
    return algoritmo, quantum, lista


# --------------------------------------------------------------------------
# 3. Linha do tempo (com união de intervalos adjacentes)
# --------------------------------------------------------------------------
class LinhaDoTempo:
    def __init__(self):
        self.intervalos = []

    def registrar(self, processo, inicio, fim):
        if fim <= inicio:
            return
        ultimo = self.intervalos[-1] if self.intervalos else None
        if ultimo and ultimo["processo"] == processo and ultimo["fim"] == inicio:
            ultimo["fim"] = fim  # une trechos consecutivos do mesmo processo
        else:
            self.intervalos.append({"processo": processo, "inicio": inicio, "fim": fim})


# --------------------------------------------------------------------------
# 2. Políticas de escalonamento
# --------------------------------------------------------------------------
def simular_srtf(processos):
    """SRTF preemptivo. Avança unidade a unidade; a cada instante admite as
    chegadas e reavalia. Como o saldo do processo atual só diminui e o dos
    outros não muda, reavaliar a cada unidade dá o mesmo resultado que
    reavaliar só em chegadas/conclusões."""
    pendentes = list(processos)          # ainda não chegaram (ordenados)
    restante = {p["id"]: p["cpu"] for p in processos}
    chegada = {p["id"]: p["chegada"] for p in processos}
    prontos = []
    primeira, conclusao = {}, {}
    linha = LinhaDoTempo()
    atual = None
    t = 0

    while pendentes or prontos:
        # admitir chegadas do instante t
        while pendentes and pendentes[0]["chegada"] <= t:
            prontos.append(pendentes.pop(0)["id"])

        if not prontos:
            # CPU ociosa até a próxima chegada
            prox = pendentes[0]["chegada"]
            linha.registrar("OCIOSO", t, prox)
            t = prox
            continue

        # escolha: menor restante; desempate geral por chegada e ID
        melhor = min(prontos, key=lambda i: (restante[i], chegada[i], i))
        if atual in prontos and restante[atual] <= restante[melhor]:
            escolhido = atual           # empate com o atual: ele fica
        else:
            escolhido = melhor          # preempção (ou CPU estava livre)

        primeira.setdefault(escolhido, t)
        linha.registrar(escolhido, t, t + 1)
        restante[escolhido] -= 1
        t += 1
        atual = escolhido

        if restante[escolhido] == 0:
            conclusao[escolhido] = t
            prontos.remove(escolhido)
            atual = None

    return linha.intervalos, primeira, conclusao


def simular_rr(processos, quantum):
    """Round Robin com fila FIFO."""
    pendentes = list(processos)
    restante = {p["id"]: p["cpu"] for p in processos}
    fila = []
    primeira, conclusao = {}, {}
    linha = LinhaDoTempo()
    t = 0

    def admitir_ate(instante):
        while pendentes and pendentes[0]["chegada"] <= instante:
            fila.append(pendentes.pop(0)["id"])

    admitir_ate(t)
    while fila or pendentes:
        if not fila:
            prox = pendentes[0]["chegada"]
            linha.registrar("OCIOSO", t, prox)
            t = prox
            admitir_ate(t)
            continue

        pid = fila.pop(0)
        fatia = min(quantum, restante[pid])
        primeira.setdefault(pid, t)
        linha.registrar(pid, t, t + fatia)
        t += fatia
        restante[pid] -= fatia

        # chegadas durante a fatia e exatamente no seu fim entram ANTES
        # da reinserção do processo interrompido
        admitir_ate(t)

        if restante[pid] == 0:
            conclusao[pid] = t
        else:
            fila.append(pid)

    return linha.intervalos, primeira, conclusao


# --------------------------------------------------------------------------
# 4. Métricas
# --------------------------------------------------------------------------
def calcular_metricas(processos, primeira, conclusao):
    resultado = []
    for p in sorted(processos, key=lambda p: p["id"]):
        pid = p["id"]
        turnaround = conclusao[pid] - p["chegada"]
        resultado.append({
            "id": pid,
            "primeira_execucao": primeira[pid],
            "conclusao": conclusao[pid],
            "turnaround": turnaround,
            "espera": turnaround - p["cpu"],
            "resposta": primeira[pid] - p["chegada"],
        })
    n = len(resultado)
    medias = {
        chave: sum(r[chave] for r in resultado) / n
        for chave in ("turnaround", "espera", "resposta")
    }
    return resultado, medias


def main():
    try:
        dados = ler_entrada(sys.stdin.read())
        algoritmo, quantum, processos = validar(dados)
    except EntradaInvalida as e:
        print(json.dumps({"erro": str(e)}, ensure_ascii=False))
        sys.exit(1)

    if algoritmo == "SRTF":
        linha, primeira, conclusao = simular_srtf(processos)
    else:
        linha, primeira, conclusao = simular_rr(processos, quantum)

    metricas, medias = calcular_metricas(processos, primeira, conclusao)
    saida = {
        "algoritmo": algoritmo,
        "linha_do_tempo": linha,
        "processos": metricas,
        "medias": medias,
    }
    print(json.dumps(saida, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()