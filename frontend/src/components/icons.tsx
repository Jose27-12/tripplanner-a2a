// Iconos SVG en línea (sin dependencias externas).
import type { SVGProps } from "react";

function Icon({ d, ...props }: SVGProps<SVGSVGElement> & { d: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round"
      strokeLinejoin="round" aria-hidden="true" {...props}>
      <path d={d} />
    </svg>
  );
}

type P = SVGProps<SVGSVGElement>;
export const IconDashboard = (p: P) => <Icon {...p} d="M3 13h8V3H3v10zm10 8h8V11h-8v10zM3 21h8v-6H3v6zm10-18v6h8V3h-8z" />;
export const IconChat = (p: P) => <Icon {...p} d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z" />;
export const IconPlane = (p: P) => <Icon {...p} d="M2.5 19.5h19M3 13.5l4 1 10-6.5c1.2-.8 2.8-.4 3.3.8.3.7 0 1.6-.7 2L8.5 17.5 3 16l-.5-2.5z" />;
export const IconSun = (p: P) => <Icon {...p} d="M12 4V2m0 20v-2m8-8h2M2 12h2m13.7-5.7 1.4-1.4M4.9 19.1l1.4-1.4m0-11.4L4.9 4.9m14.2 14.2-1.4-1.4M12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10z" />;
export const IconMap = (p: P) => <Icon {...p} d="M9 20l-6-2V4l6 2m0 14 6-2m-6 2V6m6 12 6 2V6l-6-2m0 14V4M9 6l6-2" />;
export const IconTicket = (p: P) => <Icon {...p} d="M3 8a2 2 0 0 0 2-2h14a2 2 0 0 0 2 2v2a2 2 0 0 0 0 4v2a2 2 0 0 0-2 2H5a2 2 0 0 0-2-2v-2a2 2 0 0 0 0-4V8zm10-2v12" />;
export const IconSliders = (p: P) => <Icon {...p} d="M4 6h10m4 0h2M4 12h4m4 0h8M4 18h12m4 0h0M16 4v4M10 10v4M18 16v4" />;
export const IconLogout = (p: P) => <Icon {...p} d="M15 17l5-5-5-5m5 5H9m4 9H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h8" />;
export const IconMenu = (p: P) => <Icon {...p} d="M4 6h16M4 12h16M4 18h16" />;
export const IconPlus = (p: P) => <Icon {...p} d="M12 5v14M5 12h14" />;
export const IconSend = (p: P) => <Icon {...p} d="M22 2 11 13M22 2l-7 20-4-9-9-4 20-7z" />;
export const IconCalendar = (p: P) => <Icon {...p} d="M8 3v3m8-3v3M4 9h16M5 5h14a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1z" />;
export const IconUsers = (p: P) => <Icon {...p} d="M16 20v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2m20 0v-2a4 4 0 0 0-3-3.9M16 3.1a4 4 0 0 1 0 7.8M13 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0z" />;
export const IconWallet = (p: P) => <Icon {...p} d="M3 7a2 2 0 0 1 2-2h13v4M3 7v10a2 2 0 0 0 2 2h15V9H5a2 2 0 0 1-2-2zm14 7h.01" />;
