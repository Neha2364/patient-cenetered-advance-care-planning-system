import { motion, type HTMLMotionProps } from "framer-motion";
import { forwardRef, type ReactNode } from "react";
import { cn } from "@/lib/utils";

type MotionCardProps = HTMLMotionProps<"div"> & {
  children: ReactNode;
  hoverLift?: boolean;
};

export const MotionCard = forwardRef<HTMLDivElement, MotionCardProps>(
  ({ className, children, hoverLift = true, ...rest }, ref) => (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: "easeOut" }}
      whileHover={hoverLift ? { y: -2 } : undefined}
      className={cn(
        "rounded-2xl border border-border bg-card p-5 shadow-[0_1px_2px_rgba(15,23,42,0.04),0_4px_16px_rgba(15,23,42,0.04)] transition-shadow hover:shadow-[0_10px_30px_-12px_rgba(15,23,42,0.15)]",
        className,
      )}
      {...rest}
    >
      {children}
    </motion.div>
  ),
);
MotionCard.displayName = "MotionCard";
