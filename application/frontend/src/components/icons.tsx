import type { SVGProps } from "react";

export function AiAssistantIcon({
  className = "ai-icon",
  size = 20,
  ...props
}: SVGProps<SVGSVGElement> & { size?: number }) {
  return (
    <svg
      aria-hidden="true"
      className={className}
      fill="currentColor"
      height={size}
      viewBox="0 0 24 24"
      width={size}
      {...props}
    >
      {/* Primary sparkle */}
      <path d="M12 2L14.3 7.7L20 10L14.3 12.3L12 18L9.7 12.3L4 10L9.7 7.7L12 2Z" />
      {/* Upper-right accent sparkle */}
      <path
        d="M19 15L19.9 17.1L22 18L19.9 18.9L19 21L18.1 18.9L16 18L18.1 17.1L19 15Z"
        opacity="0.8"
      />
      {/* Lower-left subtle sparkle */}
      <path
        d="M5 16L5.8 17.7L7.5 18.5L5.8 19.3L5 21L4.2 19.3L2.5 18.5L4.2 17.7L5 16Z"
        opacity="0.65"
      />
    </svg>
  );
}
