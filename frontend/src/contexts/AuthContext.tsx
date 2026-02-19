"use client"

import React, { createContext, useContext, useEffect, useState } from "react"
import { User, Session, AuthError } from "@supabase/supabase-js"
import { supabase } from "@/lib/supabase"

export interface ProfileData {
  full_name?: string
  organization?: string
  phone?: string
  job_title?: string
}

interface AuthContextType {
  user: User | null
  session: Session | null
  loading: boolean
  signIn: (email: string, password: string) => Promise<{ error: AuthError | null }>
  signUp: (
    email: string,
    password: string,
    profileData?: ProfileData
  ) => Promise<{ error: AuthError | null }>
  signOut: () => Promise<void>
  updateProfile: (profileData: ProfileData) => Promise<{ error: Error | null }>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Get initial session
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session)
      setUser(session?.user ?? null)
      setLoading(false)
    })

    // Listen for auth changes
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session)
      setUser(session?.user ?? null)
      setLoading(false)
    })

    return () => subscription.unsubscribe()
  }, [])

  const signIn = async (email: string, password: string) => {
    const { error } = await supabase.auth.signInWithPassword({
      email,
      password,
    })
    return { error }
  }

  const signUp = async (
    email: string,
    password: string,
    profileData?: ProfileData
  ) => {
    // Sign up with optional profile data in user metadata
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: profileData, // Stored in auth.users.user_metadata
        emailRedirectTo: `${window.location.origin}/login`,
      },
    })

    if (error) {
      return { error }
    }

    // If signup successful and we have profile data, update the profiles table
    // The trigger creates the row, we just need to update it with extra fields
    if (data.user && profileData) {
      const { error: profileError } = await supabase
        .from("profiles")
        .update(profileData)
        .eq("id", data.user.id)

      if (profileError) {
        console.warn("Failed to update profile:", profileError)
        // Don't fail signup if profile update fails - profile was created by trigger
      }
    }

    return { error: null }
  }

  const signOut = async () => {
    localStorage.clear()
    sessionStorage.clear()
    document.cookie.split(";").forEach((c) => {
      document.cookie = c
        .replace(/^ +/, "")
        .replace(/=.*/, "=;expires=" + new Date().toUTCString() + ";path=/")
    })
    await supabase.auth.signOut()
  }

  const updateProfile = async (profileData: ProfileData) => {
    if (!user) {
      return { error: new Error("No user logged in") }
    }

    const { error } = await supabase
      .from("profiles")
      .update(profileData)
      .eq("id", user.id)

    return { error: error ? new Error(error.message) : null }
  }

  const value = {
    user,
    session,
    loading,
    signIn,
    signUp,
    signOut,
    updateProfile,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider")
  }
  return context
}
