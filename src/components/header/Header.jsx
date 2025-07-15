import React from 'react'
import './Header.css';
import Logo from '../../assets/cit-logo.png'

const Header = () => {
  return (
    <header className="main-header">
      <img className="logo-placeholder" src={Logo}/>
    </header>
  )
}

export default Header