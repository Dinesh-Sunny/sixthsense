import { clsx, type ClassValue } from "clsx"
import { extendTailwindMerge } from "tailwind-merge"

// Our type-style utilities (globals.css @utility) are font sizes, not colours;
// without this, cn("text-label", "text-truth") would drop text-label.
const twMerge = extendTailwindMerge({
  extend: {
    classGroups: {
      "font-size": [
        { text: ["display", "title", "body", "body-sm", "label", "data", "metric", "eye", "forecast"] },
      ],
    },
  },
})

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
