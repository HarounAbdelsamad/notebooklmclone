import type { SVGProps } from "react";

/** Shared defaults for the small line-icon set used across the Studio panel. */
function IconBase(props: SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      width="18"
      height="18"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...props}
    />
  );
}

/** Document with lines — used for "summary". */
export function SummaryIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <IconBase {...props}>
      <path d="M6 2.5h8l4 4v14a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1v-17a1 1 0 0 1 1-1Z" />
      <path d="M14 2.5v4h4" />
      <path d="M8 12h8M8 15.5h8M8 8.5h4" />
    </IconBase>
  );
}

/** Speech bubble with "?" — used for "faq". */
export function FaqIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <IconBase {...props}>
      <path d="M4 5.5h16a1 1 0 0 1 1 1V15a1 1 0 0 1-1 1H9l-4.4 3.3A.5.5 0 0 1 4 18.9V16H4a1 1 0 0 1-1-1V6.5a1 1 0 0 1 1-1Z" />
      <path d="M10 9.6c0-1.1.9-2 2-2s2 .8 2 1.8c0 1.4-2 1.3-2 3.1" />
      <circle cx="12" cy="15.6" r="0.15" fill="currentColor" stroke="none" />
    </IconBase>
  );
}

/** Open book — used for "study_guide". */
export function StudyGuideIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <IconBase {...props}>
      <path d="M12 5.5c-1.5-1.2-3.6-1.7-6-1.7v13.7c2.4 0 4.5.5 6 1.7 1.5-1.2 3.6-1.7 6-1.7V3.8c-2.4 0-4.5.5-6 1.7Z" />
      <path d="M12 5.5v13.7" />
    </IconBase>
  );
}

/** Clipboard with checklist — used for "briefing". */
export function BriefingIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <IconBase {...props}>
      <rect x="5" y="3.5" width="14" height="18" rx="1.5" />
      <path d="M9 3.5V3a1.5 1.5 0 0 1 1.5-1.5h3A1.5 1.5 0 0 1 15 3v.5" />
      <path d="M8.5 10.5h7M8.5 14h7M8.5 17.5h4.5" />
    </IconBase>
  );
}

/** Clock — used for "timeline". */
export function TimelineIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <IconBase {...props}>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3.5 2" />
    </IconBase>
  );
}

/** Generic document icon — fallback for any future output type. */
export function GenericOutputIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <IconBase {...props}>
      <path d="M6 2.5h8l4 4v14a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1v-17a1 1 0 0 1 1-1Z" />
      <path d="M14 2.5v4h4" />
    </IconBase>
  );
}

/** Three vertical dots ("kebab" menu) — used for card overflow menus. */
export function MoreVerticalIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <IconBase {...props}>
      <circle cx="12" cy="5" r="1.4" fill="currentColor" stroke="none" />
      <circle cx="12" cy="12" r="1.4" fill="currentColor" stroke="none" />
      <circle cx="12" cy="19" r="1.4" fill="currentColor" stroke="none" />
    </IconBase>
  );
}

/** Trash can — used for destructive delete actions. */
export function TrashIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <IconBase {...props}>
      <path d="M4 6.5h16" />
      <path d="M8.5 6.5V4.8a1.3 1.3 0 0 1 1.3-1.3h4.4a1.3 1.3 0 0 1 1.3 1.3v1.7" />
      <path d="M6.5 6.5 7.3 19.5a1.5 1.5 0 0 0 1.5 1.4h6.4a1.5 1.5 0 0 0 1.5-1.4l.8-13" />
      <path d="M10.2 10.5v6.5M13.8 10.5v6.5" />
    </IconBase>
  );
}
