package com.syndicate.deployment.annotations;

import com.syndicate.deployment.model.lambda.url.AuthType;
import com.syndicate.deployment.model.lambda.url.InvokeMode;

import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

/**
 * Created by Roman Ivanov on 2023-11-07
 */
@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.TYPE)
public @interface LambdaUrlConfig {

    AuthType authType() default AuthType.NONE;

    InvokeMode invokeMode() default InvokeMode.BUFFERED;

}
