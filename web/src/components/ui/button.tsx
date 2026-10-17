import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"
import { Slot } from "radix-ui"

// Everything you press is a pill (DESIGN.md). 150ms ease-out on hover/press.
const buttonVariants = cva(
  "inline-flex shrink-0 items-center justify-center gap-2 rounded-full border border-transparent text-sm font-medium whitespace-nowrap transition-[background-color,color,opacity,transform] duration-150 ease-out outline-none active:scale-[0.98] focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:pointer-events-none disabled:opacity-40 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
  {
    variants: {
      variant: {
        default: "bg-pill text-on-ink hover:bg-pill/90",
        glass: "glass text-ink hover:bg-surface",
        outline: "border-hairline bg-transparent text-ink hover:bg-surface-sunk",
        ghost: "text-ink hover:bg-surface-sunk",
        link: "h-auto px-0 text-slate underline-offset-4 hover:underline",
      },
      size: {
        default: "h-10 px-[18px]",
        sm: "h-8 px-3.5 text-[13px]",
        lg: "h-12 px-6",
        icon: "size-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

function Button({
  className,
  variant = "default",
  size = "default",
  asChild = false,
  ...props
}: React.ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean
  }) {
  const Comp = asChild ? Slot.Root : "button"

  return (
    <Comp
      data-slot="button"
      data-variant={variant}
      data-size={size}
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Button, buttonVariants }
