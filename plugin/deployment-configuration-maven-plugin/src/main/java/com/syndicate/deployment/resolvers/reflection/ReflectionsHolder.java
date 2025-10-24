package com.syndicate.deployment.resolvers.reflection;

import org.reflections.Reflections;
import org.reflections.util.ClasspathHelper;
import org.reflections.util.ConfigurationBuilder;
import org.reflections.util.FilterBuilder;

import java.lang.annotation.Annotation;
import java.net.URL;
import java.util.Arrays;
import java.util.Collection;
import java.util.HashSet;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

/**
 * @author Kyrylo Andreiev
 * Created: 6/14/2025
 */
public final class ReflectionsHolder {

    private static final Map<Key, Reflections> holder = new ConcurrentHashMap<>();

    public static Set<Class<?>> getTypesAnnotatedWith(String[] packages, Class<? extends Annotation> annotation) {
        Collection<URL> urls = new HashSet<>();
        FilterBuilder filter = new FilterBuilder();
        for (String param : packages) {
            urls.addAll(ClasspathHelper.forPackage(param));
            filter.includePackage(param);
        }

        Set<Class<?>> classes = new HashSet<>();
        for (URL url : urls) {
            Reflections reflections = holder.computeIfAbsent(new Key(url, packages),
                k -> new Reflections(new ConfigurationBuilder().setUrls(url).filterInputsBy(filter)));
            classes.addAll(reflections.getTypesAnnotatedWith(annotation));
        }
        return classes;
    }

    private static class Key {

        private final URL url;
        private final String[] packages;

        public Key(URL url, String[] packages) {
            this.url = url;
            this.packages = packages;
        }

        @Override
        public boolean equals(Object o) {
            if (!(o instanceof Key)) return false;
            Key key = (Key) o;
            return Objects.equals(url, key.url) && Objects.deepEquals(packages, key.packages);
        }

        @Override
        public int hashCode() {
            return Objects.hash(url, Arrays.hashCode(packages));
        }

        @Override
        public String toString() {
            return "Key{" +
                "url=" + url +
                ", packages=" + Arrays.toString(packages) +
                '}';
        }
    }

    private ReflectionsHolder() {
        // Prevent instantiation
    }
}
