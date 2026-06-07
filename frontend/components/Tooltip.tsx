import { ReactNode, useState, useMemo, useCallback } from "react";

interface TooltipProps {
  content: string;
  children: ReactNode;
  side?: "top" | "bottom";
}

export function Tooltip({ content, children, side = "top" }: TooltipProps) {
  const [showTooltip, setShowTooltip] = useState<boolean>(false);

  const handleMouseEnter = useCallback(() => setShowTooltip(true), []);
  const handleMouseLeave = useCallback(() => setShowTooltip(false), []);

  const tooltipStyle = useMemo(() => {
    const isTop = side === "top";
    const translateY = showTooltip ? 0 : isTop ? 6 : -6;

    return {
      position: "absolute" as const,
      ...(isTop ? { bottom: "calc(100% + 8px)" } : { top: "calc(100% + 8px)" }),
      left: "50%",
      transform: `translateX(-50%) translateY(${translateY}px)`,
      background: "#1a1a1a",
      border: "1px solid #d97706",
      color: "#f5f5f5",
      padding: "8px 12px",
      borderRadius: 8,
      fontSize: 12,
      whiteSpace: "nowrap" as const,
      boxShadow: "0 4px 12px rgba(0, 0, 0, 0.5)",
      zIndex: 50,
      opacity: showTooltip ? 1 : 0,
      transition: "opacity 180ms ease, transform 180ms ease",
      pointerEvents: showTooltip ? ("auto" as const) : ("none" as const),
    };
  }, [showTooltip, side]);

  return (
    <div
      className="relative inline-block"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      {children}
      <div role="tooltip" aria-hidden={!showTooltip} style={tooltipStyle}>
        {content}
      </div>
    </div>
  );
}