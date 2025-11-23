import React, { useState } from 'react';
import { supabase } from './supabaseClient';

function Login({ onLogin }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');

  const handleLogin = async (e) => {
    e.preventDefault();
    setMessage('');
    const { data, error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) {
      setMessage(error.message);
      return;
    }
    const token = data?.session?.access_token;
    if (token) {
      localStorage.setItem('supabase_token', token);
      onLogin && onLogin(token);
      setMessage('Logged in successfully');
    } else {
      setMessage('Login succeeded but no token received.');
    }
  };

  const handleSignup = async (e) => {
    e.preventDefault();
    setMessage('');
    const { data, error } = await supabase.auth.signUp({ email, password });
    if (error) setMessage(error.message);
    else setMessage('Sign up successful — check your email for confirmation.');
  };

  return (
    <div style={{ maxWidth: 420, margin: '12px auto', textAlign: 'center' }}>
      <h3>Sign In / Sign Up</h3>
      <form onSubmit={handleLogin}>
        <input placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} style={{padding:8, width:'100%', marginBottom:8}} />
        <input placeholder="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} style={{padding:8, width:'100%', marginBottom:8}} />
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <button onClick={handleLogin} style={{ padding: '8px 16px', background:'#1976d2', color:'#fff', border:'none', borderRadius:6 }}>Login</button>
          <button onClick={handleSignup} style={{ padding: '8px 16px', background:'#4caf50', color:'#fff', border:'none', borderRadius:6 }}>Sign up</button>
        </div>
      </form>
      {message && <div style={{ marginTop: 12 }}>{message}</div>}
    </div>
  );
}

export default Login;
