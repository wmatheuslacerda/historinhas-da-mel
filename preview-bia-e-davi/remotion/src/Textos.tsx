import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {CORES, FONTE, Fala, roteiro} from './dados';

const contorno = (px: number, cor = '#1d1430'): React.CSSProperties => ({
  WebkitTextStroke: `${px}px ${cor}`,
  paintOrder: 'stroke fill',
});

type Bloco = {palavras: [string, number, number][]; ini: number; fim: number; fala: Fala};

const blocos: Bloco[] = [];
for (const fala of roteiro.falas) {
  let atual: [string, number, number][] = [];
  const grupos: [string, number, number][][] = [];
  for (const p of fala.palavras) {
    atual.push(p);
    if (atual.length >= 4 || /[.!?…:]$/.test(p[0])) {
      grupos.push(atual);
      atual = [];
    }
  }
  if (atual.length) grupos.push(atual);
  grupos.forEach((gr, i) => {
    const prox = grupos[i + 1];
    blocos.push({palavras: gr, ini: gr[0][1], fim: prox ? prox[0][1] : fala.fim + 8, fala});
  });
}

/** Legenda palavra por palavra, com a palavra falada colorida e "pulando" */
export const Legendas: React.FC = () => {
  const g = useCurrentFrame();
  const {fps} = useVideoConfig();
  const b = blocos.find((x) => g >= x.ini - 1 && g < x.fim);
  if (!b) return null;
  const cor = CORES[b.fala.voz];
  const entra = spring({frame: g - b.ini + 1, fps, config: {damping: 12, stiffness: 220}});
  const iniFala = b.fala.palavras[0][1];
  const tag = spring({frame: g - iniFala + 2, fps, config: {damping: 11, stiffness: 180}});
  const nome = b.fala.voz === 'bia' ? 'BIA' : b.fala.voz === 'davi' ? 'DAVI' : null;

  return (
    <AbsoluteFill style={{alignItems: 'center', fontFamily: FONTE}}>
      {nome ? (
        <div
          style={{
            position: 'absolute',
            top: 1265,
            padding: '8px 30px',
            borderRadius: 40,
            background: cor,
            color: '#1d1430',
            fontWeight: 700,
            fontSize: 42,
            letterSpacing: 3,
            transform: `scale(${tag}) rotate(${(1 - tag) * -8}deg)`,
            boxShadow: '0 6px 0 rgba(0,0,0,0.25)',
          }}
        >
          {nome}
        </div>
      ) : null}
      <div
        style={{
          position: 'absolute',
          top: 1355,
          width: 1000,
          textAlign: 'center',
          fontWeight: 700,
          fontSize: 86,
          lineHeight: 1.15,
          color: 'white',
          transform: `scale(${0.85 + 0.15 * entra})`,
          ...contorno(14),
          textShadow: '0 8px 0 rgba(0,0,0,0.30)',
        }}
      >
        {b.palavras.map(([w, a], i) => {
          const ativa = g >= a && (i === b.palavras.length - 1 || g < b.palavras[i + 1][1]);
          const pop = spring({frame: g - a, fps, config: {damping: 9, stiffness: 260}});
          const esc = ativa ? 1.12 - 0.06 * pop : 1;
          return (
            <span key={i} style={{display: 'inline-block', margin: '0 18px', color: ativa ? cor : 'white', transform: `scale(${esc})`}}>
              {w}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

/** Abertura: "Bia e Davi" com letras pulando */
export const Titulo: React.FC = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const sai = interpolate(f, [62, 80], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  if (f > 82) return null;
  const letras = 'Bia e Davi'.split('');
  const sub = spring({frame: f - 16, fps, config: {damping: 14}});
  return (
    <AbsoluteFill style={{alignItems: 'center', fontFamily: FONTE, opacity: 1 - sai, transform: `translateY(${-60 * sai}px)`}}>
      <div style={{position: 'absolute', top: 250, fontSize: 150, fontWeight: 700, color: 'white', ...contorno(18), textShadow: '0 10px 0 rgba(0,0,0,0.3)'}}>
        {letras.map((l, i) => {
          const s = spring({frame: f - i * 2, fps, config: {damping: 8, stiffness: 160}});
          const cor = i < 3 ? '#FFD54F' : i > 5 ? '#64C8FF' : 'white';
          return (
            <span key={i} style={{display: 'inline-block', color: cor, transform: `translateY(${(1 - s) * -200}px) scale(${s})`, minWidth: l === ' ' ? 40 : undefined}}>
              {l}
            </span>
          );
        })}
      </div>
      <div
        style={{
          position: 'absolute',
          top: 450,
          fontSize: 50,
          fontWeight: 700,
          letterSpacing: 4,
          color: '#1d1430',
          background: 'white',
          padding: '8px 34px',
          borderRadius: 50,
          opacity: sub,
          transform: `scale(${0.6 + 0.4 * sub})`,
        }}
      >
        EPISÓDIO 1 • A NOVATA
      </div>
    </AbsoluteFill>
  );
};

export const Marca: React.FC = () => {
  const f = useCurrentFrame();
  const op = interpolate(f, [80, 100], [0, 0.8], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{alignItems: 'center', fontFamily: FONTE}}>
      <div style={{position: 'absolute', top: 110, fontSize: 36, fontWeight: 500, color: 'white', opacity: op, ...contorno(4, 'rgba(0,0,0,0.6)')}}>
        @biaedaviofc
      </div>
    </AbsoluteFill>
  );
};

/** Final: "Continua..." */
export const Final: React.FC = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = spring({frame: f, fps, config: {damping: 9, stiffness: 140}});
  const s2 = spring({frame: f - 14, fps, config: {damping: 12}});
  const bate = 1 + 0.08 * Math.max(0, Math.sin((f / fps) * Math.PI * 2.4));
  const fundo = interpolate(f, [0, 20], [0, 0.55], {extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{alignItems: 'center', fontFamily: FONTE}}>
      <AbsoluteFill style={{background: `linear-gradient(180deg, rgba(20,10,30,0) 20%, rgba(20,10,30,${fundo}) 60%)`}} />
      <div style={{position: 'absolute', top: 1180, fontSize: 140, fontWeight: 700, color: 'white', transform: `scale(${s})`, ...contorno(18), textShadow: '0 10px 0 rgba(0,0,0,0.3)'}}>
        Continua...
      </div>
      <svg viewBox="0 0 20 22" width={120} height={120} style={{position: 'absolute', top: 1040, transform: `scale(${s * bate})`}}>
        <path
          d="M12 21s-7.5-4.6-10-9.3C.4 8.6 2.1 5 5.6 5c2 0 3.4 1.1 4.4 2.5C11 6.1 12.4 5 14.4 5 17.9 5 19.6 8.6 18 11.7 15.5 16.4 12 21 12 21z"
          fill="#FF6B8A"
          stroke="white"
          strokeWidth={1.2}
          transform="translate(-1 -2)"
        />
      </svg>
      <div style={{position: 'absolute', top: 1380, fontSize: 52, fontWeight: 700, color: '#FFD54F', opacity: s2, transform: `translateY(${(1 - s2) * 40}px)`, ...contorno(10)}}>
        Segue pra ver o episódio 2
      </div>
    </AbsoluteFill>
  );
};
