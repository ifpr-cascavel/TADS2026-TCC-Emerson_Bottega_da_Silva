import React from 'react';

// Small "i" help affordance. On hover or keyboard focus it reveals a short,
// plain-language explanation next to a technical parameter. It is purely
// presentational (CSS-driven) and accessible: the icon is focusable and the
// text is exposed to assistive tech through aria-label.
const InfoTooltip = ({ text, label = 'Mais informações', placement = 'left' }) => (
  <span className={`info-tooltip info-tooltip--${placement}`}>
    <button
      type="button"
      className="info-tooltip-trigger"
      aria-label={label}
      // The button never submits/acts; it only surfaces the tooltip on
      // hover/focus. Preventing the default keeps forms and clicks unaffected.
      onClick={(event) => event.preventDefault()}
    >
      i
    </button>
    <span className="info-tooltip-bubble" role="tooltip">
      {text}
    </span>
  </span>
);

export default InfoTooltip;
