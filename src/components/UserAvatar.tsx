"use client";

type UserAvatarProps = {
  photoURL?: string | null;
  displayName?: string | null;
  email?: string | null;
  sizeClassName?: string;
  className?: string;
};

export function UserAvatar({
  photoURL,
  displayName,
  email,
  sizeClassName = "h-12 w-12",
  className = "",
}: UserAvatarProps) {
  const fallbackLabel = displayName || email || "ET Compass user";
  const source = photoURL?.trim() || "/default-luna-avatar.svg";

  return (
    <div
      role="img"
      aria-label={`${fallbackLabel} avatar`}
      className={`relative overflow-hidden rounded-full border-2 border-black bg-white bg-cover bg-center bg-no-repeat shadow-[4px_4px_0px_0px_black] ${sizeClassName} ${className}`.trim()}
      style={{ backgroundImage: `url("${source}")` }}
    >
      <span className="absolute bottom-1 right-1 h-3 w-3 rounded-full border border-black bg-[#2EAF47]" />
    </div>
  );
}
