import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  User,
  Mail,
  KeyRound,
  AlertCircle,
  CheckCircle2,
  Eye,
  EyeOff,
  Shield,
  ShieldCheck,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { authService, adminService } from "@/lib/api";
import { toast } from "sonner";

export const Route = createFileRoute("/admin-dashboard/settings")({
  head: () => ({ meta: [{ title: "Admin Settings — ACP Care" }] }),
  component: AdminSettingsPage,
});

function AdminSettingsPage() {
  const qc = useQueryClient();
  const cachedUser = authService.getCurrentUser();

  const { data: profile, isLoading } = useQuery({
    queryKey: ["adminProfile"],
    queryFn: adminService.getProfile,
    initialData: cachedUser
      ? {
          user_id: cachedUser.user_id,
          full_name: cachedUser.full_name,
          email: cachedUser.email,
          role: cachedUser.role,
        }
      : undefined,
  });

  const currentEmail = profile?.email || cachedUser?.email || "";
  const fullName = profile?.full_name || cachedUser?.full_name || "Administrator";
  const userId = profile?.user_id || cachedUser?.user_id;

  // Edit Email Form State
  const [newEmail, setNewEmail] = useState("");
  const [emailPassword, setEmailPassword] = useState("");
  const [showEmailPassword, setShowEmailPassword] = useState(false);
  const [emailError, setEmailError] = useState("");

  // Change Password Form State
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [passwordError, setPasswordError] = useState("");

  // Email Mutation
  const emailMutation = useMutation({
    mutationFn: () =>
      adminService.changeEmail({
        new_email: newEmail.trim().toLowerCase(),
        password: emailPassword,
      }),
    onSuccess: (data) => {
      toast.success(data?.message || "Email address updated successfully.");
      setEmailError("");
      setNewEmail("");
      setEmailPassword("");
      qc.invalidateQueries({ queryKey: ["adminProfile"] });
    },
    onError: (err: any) => {
      const msg = err?.message || "Failed to update email address.";
      setEmailError(msg);
      toast.error(msg);
    },
  });

  // Password Mutation
  const passwordMutation = useMutation({
    mutationFn: () =>
      adminService.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: confirmPassword,
      }),
    onSuccess: (data) => {
      toast.success(data?.message || "Password changed successfully.");
      setPasswordError("");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      qc.invalidateQueries({ queryKey: ["adminProfile"] });
    },
    onError: (err: any) => {
      const msg = err?.message || "Failed to change password.";
      setPasswordError(msg);
      toast.error(msg);
    },
  });

  const handleEmailSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setEmailError("");

    const cleanNewEmail = newEmail.trim().toLowerCase();
    if (!cleanNewEmail) {
      const msg = "New email address is required.";
      setEmailError(msg);
      toast.error(msg);
      return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(cleanNewEmail)) {
      const msg = "Please enter a valid email address (e.g., admin@example.com).";
      setEmailError(msg);
      toast.error(msg);
      return;
    }

    if (cleanNewEmail === currentEmail.toLowerCase()) {
      const msg = "New email address must be different from your current email.";
      setEmailError(msg);
      toast.error(msg);
      return;
    }

    if (!emailPassword) {
      const msg = "Current password verification is required to change email.";
      setEmailError(msg);
      toast.error(msg);
      return;
    }

    emailMutation.mutate();
  };

  const handlePasswordSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordError("");

    if (!currentPassword) {
      const msg = "Current password is required.";
      setPasswordError(msg);
      toast.error(msg);
      return;
    }

    if (!newPassword) {
      const msg = "New password is required.";
      setPasswordError(msg);
      toast.error(msg);
      return;
    }

    if (newPassword.length < 6) {
      const msg = "New password must be at least 6 characters long.";
      setPasswordError(msg);
      toast.error(msg);
      return;
    }

    if (newPassword !== confirmPassword) {
      const msg = "New password and confirmation do not match.";
      setPasswordError(msg);
      toast.error(msg);
      return;
    }

    if (currentPassword === newPassword) {
      const msg = "New password must be different from your current password.";
      setPasswordError(msg);
      toast.error(msg);
      return;
    }

    passwordMutation.mutate();
  };

  return (
    <div className="mx-auto max-w-lg space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-foreground">Account Settings</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Manage your administrator profile, email address, and account credentials.
        </p>
      </div>

      {/* Account Profile Card */}
      <div className="rounded-2xl border border-border bg-white p-6 shadow-sm space-y-4">
        <div className="flex items-center justify-between border-b border-border pb-4">
          <div className="flex items-center gap-3">
            <div className="grid h-10 w-10 place-items-center rounded-xl bg-primary/10 text-primary">
              <User className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-foreground">{fullName}</h2>
              <p className="text-xs text-muted-foreground">{currentEmail}</p>
            </div>
          </div>
          <Badge
            variant="outline"
            className="border-primary/25 bg-primary/5 text-primary text-[11px] font-semibold"
          >
            Administrator
          </Badge>
        </div>

        <div className="grid grid-cols-1 gap-4 text-sm sm:grid-cols-2 pt-1">
          <div>
            <div className="text-xs font-medium text-muted-foreground">Full Name</div>
            <div className="mt-0.5 font-medium text-foreground">{fullName}</div>
          </div>
          <div>
            <div className="text-xs font-medium text-muted-foreground">Role</div>
            <div className="mt-0.5 font-medium text-foreground">Administrator</div>
          </div>
          <div>
            <div className="text-xs font-medium text-muted-foreground">Current Email</div>
            <div className="mt-0.5 font-medium text-foreground break-all">{currentEmail}</div>
          </div>
          <div>
            <div className="text-xs font-medium text-muted-foreground">Account Status</div>
            <div className="mt-0.5 flex items-center gap-1.5 font-medium text-green-700">
              <span className="h-2 w-2 rounded-full bg-green-600" />
              Active
            </div>
          </div>
        </div>
      </div>

      {/* Edit Email Section */}
      <div className="rounded-2xl border border-border bg-white p-6 shadow-sm space-y-4">
        <div className="flex items-start gap-3 border-b border-border pb-4">
          <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-blue-50 text-blue-700">
            <Mail className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-foreground">Edit Email Address</h2>
            <p className="text-xs text-muted-foreground">
              Update your administrator login email. Requires your current password to verify identity.
            </p>
          </div>
        </div>

        <form onSubmit={handleEmailSubmit} className="space-y-4">
          {emailError && (
            <div className="flex items-center gap-2.5 rounded-xl border border-destructive/20 bg-destructive/5 px-4 py-3 text-xs text-destructive">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{emailError}</span>
            </div>
          )}

          <div className="space-y-1.5">
            <Label htmlFor="current-email" className="text-xs font-medium text-muted-foreground">
              Current Email
            </Label>
            <Input
              id="current-email"
              value={currentEmail}
              readOnly
              disabled
              className="h-11 rounded-xl bg-surface text-muted-foreground font-medium"
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="new-email" className="text-xs font-medium">
              New Email Address <span className="text-destructive">*</span>
            </Label>
            <Input
              id="new-email"
              type="email"
              placeholder="e.g. newadmin@example.com"
              value={newEmail}
              onChange={(e) => setNewEmail(e.target.value)}
              className="h-11 rounded-xl"
              required
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="email-password-verify" className="text-xs font-medium">
              Password Verification <span className="text-destructive">*</span>
            </Label>
            <div className="relative">
              <Input
                id="email-password-verify"
                type={showEmailPassword ? "text" : "password"}
                placeholder="Enter current password to confirm"
                value={emailPassword}
                onChange={(e) => setEmailPassword(e.target.value)}
                className="h-11 rounded-xl pr-10"
                required
              />
              <button
                type="button"
                onClick={() => setShowEmailPassword(!showEmailPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                aria-label={showEmailPassword ? "Hide password" : "Show password"}
              >
                {showEmailPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
            <p className="text-[11px] text-muted-foreground">
              Enter your current administrator password to authorize this email update.
            </p>
          </div>

          <Button
            type="submit"
            disabled={emailMutation.isPending}
            className="h-11 w-full rounded-xl"
          >
            {emailMutation.isPending ? "Updating Email..." : "Update Email Address"}
          </Button>
        </form>
      </div>

      {/* Change Password Section */}
      <div className="rounded-2xl border border-border bg-white p-6 shadow-sm space-y-4">
        <div className="flex items-start gap-3 border-b border-border pb-4">
          <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-amber-50 text-amber-700">
            <KeyRound className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-foreground">Change Password</h2>
            <p className="text-xs text-muted-foreground">
              Update your account password. Choose a strong password with at least 6 characters.
            </p>
          </div>
        </div>

        <form onSubmit={handlePasswordSubmit} className="space-y-4">
          {passwordError && (
            <div className="flex items-center gap-2.5 rounded-xl border border-destructive/20 bg-destructive/5 px-4 py-3 text-xs text-destructive">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{passwordError}</span>
            </div>
          )}

          <div className="space-y-1.5">
            <Label htmlFor="current-password" className="text-xs font-medium">
              Current Password <span className="text-destructive">*</span>
            </Label>
            <div className="relative">
              <Input
                id="current-password"
                type={showCurrentPassword ? "text" : "password"}
                placeholder="Enter your current password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                className="h-11 rounded-xl pr-10"
                required
              />
              <button
                type="button"
                onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                aria-label={showCurrentPassword ? "Hide password" : "Show password"}
              >
                {showCurrentPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="new-password" className="text-xs font-medium">
              New Password <span className="text-destructive">*</span>
            </Label>
            <div className="relative">
              <Input
                id="new-password"
                type={showNewPassword ? "text" : "password"}
                placeholder="At least 6 characters"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="h-11 rounded-xl pr-10"
                required
              />
              <button
                type="button"
                onClick={() => setShowNewPassword(!showNewPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                aria-label={showNewPassword ? "Hide password" : "Show password"}
              >
                {showNewPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="confirm-password" className="text-xs font-medium">
              Confirm New Password <span className="text-destructive">*</span>
            </Label>
            <div className="relative">
              <Input
                id="confirm-password"
                type={showConfirmPassword ? "text" : "password"}
                placeholder="Re-enter your new password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="h-11 rounded-xl pr-10"
                required
              />
              <button
                type="button"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                aria-label={showConfirmPassword ? "Hide password" : "Show password"}
              >
                {showConfirmPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>

          <Button
            type="submit"
            disabled={passwordMutation.isPending}
            className="h-11 w-full rounded-xl"
          >
            {passwordMutation.isPending ? "Updating Password..." : "Update Password"}
          </Button>
        </form>
      </div>
    </div>
  );
}
