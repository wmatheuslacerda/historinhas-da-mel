import roteiroJson from '../public/roteiro.json';
import camadasJson from '../public/camadas/camadas.json';
import olhosJson from '../public/olhos.json';
import {loadFont} from '@remotion/fonts';
import {staticFile} from 'remotion';

export type Voz = 'narrador' | 'bia' | 'davi';
export type Fala = {voz: Voz; cena: number; texto: string; ini: number; fim: number; palavras: [string, number, number][]};
export type Roteiro = {fps: number; duracao: number; cenas: {ini: number; fim: number}[]; falas: Fala[]; fala: Record<Voz, number[]>};
export type Camada = {cena: number; x: number; y: number; w: number; h: number};
export type Olho = {cx: number; cy: number; rx: number; ry: number; pele: string};

export const roteiro = roteiroJson as unknown as Roteiro;
export const camadas = camadasJson as unknown as Record<string, Camada>;
export const olhos = olhosJson as unknown as Record<string, Olho[]>;

// Palco = tamanho das imagens ampliadas; é escalado para cobrir 1080x1920
export const SW = 1144;
export const SH = 2048;
export const ESCALA = 1080 / SW;
export const OFF_Y = (1920 - SH * ESCALA) / 2;
export const SOBREPOE = 12; // quadros de transição entre cenas

export const CORES: Record<Voz, string> = {narrador: '#FFE7A3', bia: '#FFD54F', davi: '#64C8FF'};

export const FONTE = 'Poppins';
loadFont({family: FONTE, url: staticFile('fontes/Poppins-Bold.ttf'), weight: '700'});
loadFont({family: FONTE, url: staticFile('fontes/Poppins-Medium.ttf'), weight: '500'});

/** intensidade da voz (0..1) suavizada no quadro global g */
export const intensidade = (voz: Voz, g: number) => {
  const a = roteiro.fala[voz];
  let s = 0;
  let n = 0;
  for (let k = g - 2; k <= g + 1; k++) {
    if (k >= 0 && k < a.length) {
      s += a[k];
      n++;
    }
  }
  return n ? s / n : 0;
};
