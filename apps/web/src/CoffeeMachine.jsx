import React from 'react';

export function CoffeeMachine({ on }) {
  return <svg className={`coffee-art${on ? ' is-on' : ''}`} viewBox="0 0 460 330" role="img" aria-label={on ? 'Coffee machine brewing with flowing coffee and rising steam' : 'Coffee machine switched off'}>
    <defs><linearGradient id="machine-metal" x1="0" x2="1"><stop stopColor="#b4c5bc" /><stop offset=".45" stopColor="#eef2ed" /><stop offset="1" stopColor="#9aafa2" /></linearGradient></defs>
    <ellipse cx="230" cy="309" rx="168" ry="12" fill="#dce5d8" />
    <rect x="92" y="28" width="276" height="258" rx="24" fill="#193b33" />
    <rect x="109" y="44" width="242" height="87" rx="15" fill="url(#machine-metal)" />
    <rect x="134" y="61" width="105" height="44" rx="7" fill="#243e36" />
    <text className="machine-display" x="186" y="88" textAnchor="middle" fill="#d8e9bd" fontSize="12" fontFamily="monospace">{on ? 'BREWING' : 'STANDBY'}</text>
    <circle cx="285" cy="84" r="19" fill="#edf0e9" stroke="#758f7d" strokeWidth="4" />
    <circle className="power-light" cx="327" cy="83" r="6" />
    <rect x="135" y="139" width="189" height="117" rx="8" fill="#102a24" />
    <rect x="190" y="131" width="81" height="23" rx="6" fill="#92a99a" />
    <path d="M205 152v14m50-14v14" stroke="#becbc2" strokeWidth="8" />
    <path className="coffee-stream" d="M205 167v65M255 167v65" stroke="#b8793f" strokeWidth="5" strokeDasharray="10 4" />
    <g className="coffee-steam" fill="none" stroke="#c9d7cc" strokeWidth="3" strokeLinecap="round"><path d="M220 208c-12-12 10-18 0-32" /><path d="M239 205c12-12-10-18 0-32" /></g>
    <path d="M181 222h94v22c0 27-18 42-47 42s-47-15-47-42z" fill="#f2ead8" />
    <path d="M275 232h9c27 0 25 35-10 34" fill="none" stroke="#f2ead8" strokeWidth="10" />
    <ellipse cx="228" cy="223" rx="47" ry="8" fill="#d6c8a9" />
    <ellipse className="coffee-surface" cx="228" cy="223" rx="39" ry="5" fill="#8b512d" />
    <rect x="108" y="285" width="244" height="16" rx="6" fill="url(#machine-metal)" />
    <path d="M131 288h198M131 294h198" stroke="#7e9585" strokeWidth="2" />
  </svg>;
}
