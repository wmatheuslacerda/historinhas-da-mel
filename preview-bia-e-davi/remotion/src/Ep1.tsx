import {AbsoluteFill, Audio, Sequence, staticFile} from 'remotion';
import {Cena} from './Cena';
import {roteiro, SOBREPOE} from './dados';
import {Coracoes, Estrelas, Poeira, Raios, Vinheta} from './Efeitos';
import {Personagem} from './Personagem';
import {Final, Legendas, Marca, Titulo} from './Textos';

const C = roteiro.cenas;
const F = roteiro.falas;
const ultima = C.length - 1;
const de = (i: number) => (i === 0 ? 0 : C[i].ini - SOBREPOE);
const dur = (i: number) => C[i].fim - de(i) + (i < ultima ? SOBREPOE : 0);

// momentos importantes (quadros locais de cada cena)
const riuGlobal = F[6].palavras[F[6].palavras.length - 1][1];
const riu = riuGlobal - de(4);
const daviFala5 = {ini: F[7].ini - de(4), fim: F[7].fim - de(4)};
const saidaDavi = F[9].fim - de(5) + 2;

export const Ep1: React.FC = () => {
  return (
    <AbsoluteFill style={{background: '#000'}}>
      <Audio src={staticFile('audio.wav')} />
      <Sequence from={de(2) + 6} durationInFrames={30}>
        <Audio src={staticFile('whoosh.wav')} volume={0.8} />
      </Sequence>

      {/* 1 — A Bia chega com medo */}
      <Sequence from={de(0)} durationInFrames={dur(0)}>
        <Cena
          n={1}
          primeira
          duracao={dur(0)}
          camera={{fx: 480, fy: 1120, s0: 1.0, s1: 1.14}}
          palco={
            <Personagem
              nome="1_bia"
              pivo={[464, 1860]}
              inicioGlobal={de(0)}
              sombra={{x: 464, y: 1858, w: 300, h: 60}}
              anim={{respira: 0.012, balanco: 0.35, tremor: 1.3, fala: ['bia'], falaAmp: 10, piscar: true, seed: 1}}
            />
          }
          tela={
            <>
              <Poeira cor="#ffffff" n={18} seed="c1" brilho={0.7} />
              <Vinheta forca={0.45} />
            </>
          }
        />
      </Sequence>

      {/* 2 — Sozinha no quarto, a mãe chora no corredor */}
      <Sequence from={de(1)} durationInFrames={dur(1)}>
        <Cena
          n={2}
          duracao={dur(1)}
          camera={{fx: 380, fy: 1080, s0: 1.04, s1: 1.13, px: 20}}
          tom="rgba(175,195,245,0.55)"
          palco={
            <>
              <Personagem nome="2_mae" pivo={[990, 1360]} inicioGlobal={de(1)} anim={{respira: 0.006, soluco: true, balanco: 0.2, seed: 7}} />
              <Personagem
                nome="2_bia"
                pivo={[380, 1520]}
                inicioGlobal={de(1)}
                anim={{respira: 0.01, periodo: 4.4, balanco: 0.3, piscar: true, seed: 2}}
              />
            </>
          }
          tela={
            <>
              <Poeira cor="#d6e4ff" n={16} seed="c2" brilho={0.6} />
              <Vinheta forca={0.6} />
            </>
          }
        />
      </Sequence>

      {/* 3 — O Davi chega deslizando no soro */}
      <Sequence from={de(2)} durationInFrames={dur(2)}>
        <Cena
          n={3}
          duracao={dur(2)}
          camera={{fx: 640, fy: 900, s0: 1.12, s1: 1.03, tremer: {quadro: 30, amp: 10}}}
          palco={
            <Personagem
              nome="3_davi"
              pivo={[640, 1640]}
              inicioGlobal={de(2)}
              sombra={{x: 640, y: 1650, w: 460, h: 80}}
              anim={{entrada: {dx: -950, dy: 30, inicio: 8}, fala: ['davi'], falaAmp: 12, balanco: 0.7, respira: 0.01, piscar: true, seed: 3}}
            />
          }
          tela={
            <>
              <Poeira cor="#fff6dd" n={16} seed="c3" />
              <Vinheta forca={0.4} />
            </>
          }
        />
      </Sequence>

      {/* 4 — "Aqui a gente fala: em missão" */}
      <Sequence from={de(3)} durationInFrames={dur(3)}>
        <Cena
          n={4}
          duracao={dur(3)}
          camera={{fx: 560, fy: 950, s0: 1.03, s1: 1.1}}
          palco={
            <>
              <Personagem
                nome="4_bia"
                pivo={[300, 1300]}
                inicioGlobal={de(3)}
                anim={{respira: 0.012, fala: ['bia'], falaAmp: 10, piscar: true, seed: 4, inclinaQuando: {voz: 'davi', graus: 2.5}}}
              />
              <Personagem
                nome="4_davi"
                pivo={[800, 1360]}
                inicioGlobal={de(3)}
                anim={{respira: 0.01, fala: ['davi'], falaAmp: 12, soVertical: true, balanco: 0, piscar: true, seed: 5}}
              />
            </>
          }
          tela={
            <>
              <Raios />
              <Poeira cor="#ffd9a0" n={24} seed="c4" />
              <Vinheta forca={0.45} />
            </>
          }
        />
      </Sequence>

      {/* 5 — A Bia ri pela primeira vez */}
      <Sequence from={de(4)} durationInFrames={dur(4)}>
        <Cena
          n={5}
          duracao={dur(4)}
          camera={{fx: 580, fy: 1000, s0: 1.06, s1: 1.15}}
          palco={
            <Personagem
              nome="5_dupla"
              pivo={[600, 1380]}
              inicioGlobal={de(4)}
              anim={{
                respira: 0.012,
                fala: ['davi'],
                falaAmp: 8,
                seed: 6,
                risada: [
                  {ini: 0, fim: riu - 8, amp: 0.22},
                  {ini: riu - 2, fim: daviFala5.ini - 3, amp: 1},
                  {ini: daviFala5.ini, fim: daviFala5.fim, amp: 0.25},
                ],
              }}
            />
          }
          tela={
            <>
              <Raios />
              <Poeira cor="#ffd9a0" n={24} seed="c5" />
              <Coracoes ini={riu} fim={daviFala5.ini + 40} seed="h5" n={14} />
              <Vinheta forca={0.4} />
            </>
          }
        />
      </Sequence>

      {/* 6 — "Amanhã eu te conto o segredo" */}
      <Sequence from={de(5)} durationInFrames={dur(5)}>
        <Cena
          n={6}
          duracao={dur(5)}
          camera={{fx: 700, fy: 950, s0: 1.0, s1: 1.08}}
          palco={
            <Personagem
              nome="6_davi"
              pivo={[700, 1720]}
              inicioGlobal={de(5)}
              sombra={{x: 830, y: 1735, w: 720, h: 90}}
              anim={{fala: ['davi'], falaAmp: 12, respira: 0.012, balanco: 0.8, seed: 8, saida: {dx: 1000, dy: 0, inicio: saidaDavi, dur: 26}}}
            />
          }
          tela={
            <>
              <Raios />
              <Poeira cor="#ffd9a0" n={20} seed="c6" />
              <Estrelas seed="e6" n={9} />
              <Vinheta forca={0.45} />
            </>
          }
        />
      </Sequence>

      <Titulo />
      <Marca />
      <Legendas />
      <Sequence from={roteiro.duracao - 80}>
        <Final />
      </Sequence>
    </AbsoluteFill>
  );
};
