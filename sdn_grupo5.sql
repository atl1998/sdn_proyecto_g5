-- MySQL Workbench Forward Engineering

SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;
SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION';

-- -----------------------------------------------------
-- Schema mydb
-- -----------------------------------------------------
CREATE SCHEMA IF NOT EXISTS `mydb` DEFAULT CHARACTER SET utf8 ;
USE `mydb` ;

-- -----------------------------------------------------
-- Table `cursos`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `cursos` (
  `idcursos` INT NOT NULL,
  `nombrecurso` VARCHAR(45) NULL,
  `codigocurso` VARCHAR(45) NULL,
  PRIMARY KEY (`idcursos`)
) ENGINE = InnoDB;

-- -----------------------------------------------------
-- Table `rol`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `rol` (
  `idrol` INT NOT NULL,
  `nombrerol` VARCHAR(45) NULL,
  PRIMARY KEY (`idrol`)
) ENGINE = InnoDB;

-- -----------------------------------------------------
-- Table `usuarios`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `usuarios` (
  `idusuarios` INT NOT NULL,
  `nombreusuario` VARCHAR(45) NULL,
  `codigousuario` VARCHAR(45) NULL,
  `rol_idrol` INT NOT NULL,
  PRIMARY KEY (`idusuarios`),
  INDEX `fk_usuarios_rol_idx` (`rol_idrol` ASC) VISIBLE,
  CONSTRAINT `fk_usuarios_rol`
    FOREIGN KEY (`rol_idrol`)
    REFERENCES `rol` (`idrol`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION
) ENGINE = InnoDB;

-- -----------------------------------------------------
-- Table `servicios`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `servicios` (
  `idservicios` INT NOT NULL,
  `nombreservicio` VARCHAR(45) NULL,
  `puerto` VARCHAR(45) NULL,
  `cursos_idcursos` INT NOT NULL,
  PRIMARY KEY (`idservicios`),
  INDEX `fk_servicios_cursos1_idx` (`cursos_idcursos` ASC) VISIBLE,
  CONSTRAINT `fk_servicios_cursos1`
    FOREIGN KEY (`cursos_idcursos`)
    REFERENCES `cursos` (`idcursos`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION
) ENGINE = InnoDB;

-- -----------------------------------------------------
-- Table `cursos_has_usuarios`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `cursos_has_usuarios` (
  `cursos_idcursos` INT NOT NULL,
  `usuarios_idusuarios` INT NOT NULL,
  PRIMARY KEY (`cursos_idcursos`, `usuarios_idusuarios`),
  INDEX `fk_cursos_has_usuarios_usuarios1_idx` (`usuarios_idusuarios` ASC) VISIBLE,
  INDEX `fk_cursos_has_usuarios_cursos1_idx` (`cursos_idcursos` ASC) VISIBLE,
  CONSTRAINT `fk_cursos_has_usuarios_cursos1`
    FOREIGN KEY (`cursos_idcursos`)
    REFERENCES `cursos` (`idcursos`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION,
  CONSTRAINT `fk_cursos_has_usuarios_usuarios1`
    FOREIGN KEY (`usuarios_idusuarios`)
    REFERENCES `usuarios` (`idusuarios`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION
) ENGINE = InnoDB;

-- -----------------------------------------------------
-- Inserts de datos
-- -----------------------------------------------------
-- Solo 2 roles: Alumno (1) y Docente (2)
-- Roles
INSERT INTO rol (idrol, nombrerol) VALUES (1, 'alumno');
INSERT INTO rol (idrol, nombrerol) VALUES (2, 'docente');

-- Cursos
INSERT INTO cursos (idcursos, nombrecurso, codigocurso) VALUES (1, 'Circuitos', 'TEL180');
INSERT INTO cursos (idcursos, nombrecurso, codigocurso) VALUES (2, 'IOT', '1TEL05');
INSERT INTO cursos (idcursos, nombrecurso, codigocurso) VALUES (3, 'SDN', 'TEL354');

-- Usuarios: Profesores (rol_idrol = 2)
INSERT INTO usuarios (idusuarios, nombreusuario, codigousuario, rol_idrol) VALUES (1, 'Isaac Huamani', '20215421', 2);
INSERT INTO usuarios (idusuarios, nombreusuario, codigousuario, rol_idrol) VALUES (2, 'Carmen Vega', '20204591', 2);
INSERT INTO usuarios (idusuarios, nombreusuario, codigousuario, rol_idrol) VALUES (3, 'Jostin Pino', '20213830', 2); 

-- Usuarios: Alumnos (rol_idrol = 1)
INSERT INTO usuarios (idusuarios, nombreusuario, codigousuario, rol_idrol) VALUES (4, 'Kiara Ccala', '20206303', 1);
INSERT INTO usuarios (idusuarios, nombreusuario, codigousuario, rol_idrol) VALUES (5, 'Adrian Tipo', '20206466', 1);
INSERT INTO usuarios (idusuarios, nombreusuario, codigousuario, rol_idrol) VALUES (6, 'Alejandro Gomez', '20070429', 1);
INSERT INTO usuarios (idusuarios, nombreusuario, codigousuario, rol_idrol) VALUES (7, 'Luis Ramos', '20215987', 1);
INSERT INTO usuarios (idusuarios, nombreusuario, codigousuario, rol_idrol) VALUES (8, 'Pedro Torres', '20217891', 1);
INSERT INTO usuarios (idusuarios, nombreusuario, codigousuario, rol_idrol) VALUES (9, 'Sandra López', '20219001', 1);

-- Servicios
INSERT INTO servicios (idservicios, nombreservicio, puerto, cursos_idcursos) VALUES (1, 'http', '80', 1);
INSERT INTO servicios (idservicios, nombreservicio, puerto, cursos_idcursos) VALUES (2, 'ftp', '21', 2);
INSERT INTO servicios (idservicios, nombreservicio, puerto, cursos_idcursos) VALUES (3, 'dns', '53', 3);

-- Asociación cursos - usuarios
-- Profesores
INSERT INTO cursos_has_usuarios (cursos_idcursos, usuarios_idusuarios) VALUES (1, 1);
INSERT INTO cursos_has_usuarios (cursos_idcursos, usuarios_idusuarios) VALUES (2, 2);
INSERT INTO cursos_has_usuarios (cursos_idcursos, usuarios_idusuarios) VALUES (3, 3);

-- Alumnos:
-- Curso cicuitos (ID 1): Kiara, Adrian, Lucia
INSERT INTO cursos_has_usuarios (cursos_idcursos, usuarios_idusuarios) VALUES (1, 4); -- Kiara
INSERT INTO cursos_has_usuarios (cursos_idcursos, usuarios_idusuarios) VALUES (1, 5); -- Adrian
INSERT INTO cursos_has_usuarios (cursos_idcursos, usuarios_idusuarios) VALUES (1, 7); -- Lucia

-- Curso iot (ID 2): Alejandro, Kiara, Pedro
INSERT INTO cursos_has_usuarios (cursos_idcursos, usuarios_idusuarios) VALUES (2, 6); -- Alejandro
INSERT INTO cursos_has_usuarios (cursos_idcursos, usuarios_idusuarios) VALUES (2, 4); -- Kiara
INSERT INTO cursos_has_usuarios (cursos_idcursos, usuarios_idusuarios) VALUES (2, 8); -- Pedro

-- Curso SDN (ID 3): Adrian, Alejandro, Sandra
INSERT INTO cursos_has_usuarios (cursos_idcursos, usuarios_idusuarios) VALUES (3, 5); -- Adrian
INSERT INTO cursos_has_usuarios (cursos_idcursos, usuarios_idusuarios) VALUES (3, 6); -- Alejandro
INSERT INTO cursos_has_usuarios (cursos_idcursos, usuarios_idusuarios) VALUES (3, 9); -- Sandra

-- Restaurar configuraciones previas
SET SQL_MODE=@OLD_SQL_MODE;
SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS;
