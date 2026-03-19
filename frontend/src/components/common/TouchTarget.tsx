import { forwardRef, type ButtonHTMLAttributes, type AnchorHTMLAttributes, type ReactNode } from 'react';

interface TouchTargetBaseProps {
  children: ReactNode;
  className?: string;
}

type TouchButtonProps = TouchTargetBaseProps &
  Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'className'> & { as?: 'button' };

type TouchAnchorProps = TouchTargetBaseProps &
  Omit<AnchorHTMLAttributes<HTMLAnchorElement>, 'className'> & { as: 'a'; href: string };

type TouchDivProps = TouchTargetBaseProps & {
  as: 'div'; onClick?: () => void; role?: string; tabIndex?: number;
};

export type TouchTargetProps = TouchButtonProps | TouchAnchorProps | TouchDivProps;

const baseClasses = 'relative inline-flex items-center justify-center min-w-[44px] min-h-[44px] touch-manipulation';

export const TouchTarget = forwardRef<
  HTMLButtonElement | HTMLAnchorElement | HTMLDivElement,
  TouchTargetProps
>((props, ref) => {
  const { children, className = '', ...rest } = props;
  const classes = `${baseClasses} ${className}`;

  if (rest.as === 'a') {
    const { as: _as, ...anchorProps } = rest as TouchAnchorProps & { as: 'a' };
    return <a ref={ref as React.Ref<HTMLAnchorElement>} className={classes} {...anchorProps}>{children}</a>;
  }

  if (rest.as === 'div') {
    const { as: _as, ...divProps } = rest as TouchDivProps & { as: 'div' };
    return <div ref={ref as React.Ref<HTMLDivElement>} className={classes} {...divProps}>{children}</div>;
  }

  const { as: _as, ...buttonProps } = rest as TouchButtonProps & { as?: 'button' };
  return <button ref={ref as React.Ref<HTMLButtonElement>} type="button" className={classes} {...buttonProps}>{children}</button>;
});

TouchTarget.displayName = 'TouchTarget';
